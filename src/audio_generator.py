"""Audio stage: synthesize the dialogue and mix the final episode.

The whole conversation is sent to Gemini's multi-speaker TTS in a single
request instead of one request per line. Synthesizing turn by turn would make
each clip sound like a separate take; one request lets the model keep a
consistent pacing and intonation across the exchange, at the cost of a long
call (see the client timeout below).

Post-production is done locally with pydub (which requires FFmpeg): intro,
voices and outro are concatenated, then laid over a looping music bed.
"""

import wave
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from pydub import AudioSegment

from src import config
from src.script_generator import load_script_blocks

TTS_MODEL = "gemini-2.5-pro-preview-tts"

# google-genai reads this timeout in milliseconds: 1,000,000 ms is ~16 minutes.
# A full 5-7 minute episode is generated in one call and routinely outlives the
# client's default timeout, which would abort a request that is still working.
TTS_TIMEOUT_MS = 1_000_000

# Gemini TTS returns raw 16-bit mono PCM at 24 kHz with no container.
PCM_CHANNELS = 1
PCM_SAMPLE_RATE = 24_000
PCM_SAMPLE_WIDTH_BYTES = 2

# Mix levels in dB, relative to each source file.
VOICE_GAIN_DB = 2
JINGLE_GAIN_DB = -3
# Low enough to sit under speech without masking consonants.
MUSIC_BED_GAIN_DB = -30
MUSIC_FADE_IN_MS = 2_000
MUSIC_FADE_OUT_MS = 3_000

SPEAKER_VOICES = {"Tony": "Enceladus", "Gabriela": "Erinome"}

VOICE_DIRECTION = (
    "Role: Professional Voice Director for a top-tier tech podcast.\n"
    "Task: Perform the following script with high realism.\n\n"
    "CHARACTER PROFILES:\n"
    "1. Tony (Male): The Host. Deep male voice, energetic, articulate. Uses natural intonation. Speaks with a standard Peninsular Spanish accent (Madrid).\n"
    "2. Gabriela (Female): The Expert. Clear female voice, intelligent, calm. Peninsular Spanish accent.\n\n"
    "PERFORMANCE RULES:\n"
    "- LANGUAGE: Spanish (Spain). Pronounce 'z' and 'c' as 'th' (Distinción).\n"
    "- TONE: Conversational. Avoid the 'news reader' monotone.\n"
    "- PACING: Speakers speak really fast, typical of Spanish language.\n\n"
    "SCRIPT START:\n"
)

OUTPUT_FILENAMES = {
    "deep_dive": "podcast_final.mp3",
    "newsletter": "podcast_final_newsletter.mp3",
    "basics": "podcast_final_basic.mp3",
}


def write_wav_file(path: Path, pcm_data: bytes) -> None:
    """Wrap the raw PCM returned by the TTS model in a WAV container."""
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(PCM_CHANNELS)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)
        wav_file.setframerate(PCM_SAMPLE_RATE)
        wav_file.writeframes(pcm_data)


def _load_jingle(filename: str) -> AudioSegment:
    """Load an intro/outro from assets/, or silence if the file is absent.

    Jingles are optional so the pipeline still produces an episode on a fresh
    clone that has no audio assets yet.
    """
    path = config.ASSETS_DIR / filename
    if not path.exists():
        return AudioSegment.silent(duration=0)
    return AudioSegment.from_mp3(path) + JINGLE_GAIN_DB


def _mix_episode(voice_track: AudioSegment) -> AudioSegment:
    """Assemble intro + voices + outro over a background music bed."""
    episode = _load_jingle("intro2.mp3") + voice_track + _load_jingle("outro2.mp3")

    music_path = config.ASSETS_DIR / "background.mp3"
    if not music_path.exists():
        return episode

    music = AudioSegment.from_mp3(music_path) + MUSIC_BED_GAIN_DB
    if len(music) < len(episode):
        # Loop the track until it covers the episode. The extra repetition
        # guarantees the loop is never short by a fraction of a track before
        # it is trimmed to the exact length below.
        repetitions = len(episode) // len(music) + 2
        music = music * repetitions
    music = music[: len(episode)].fade_in(MUSIC_FADE_IN_MS).fade_out(MUSIC_FADE_OUT_MS)

    return music.overlay(episode)


def generate_podcast(script_path: str, mode: str = "deep_dive") -> Optional[str]:
    """Synthesize a script and export the mixed episode as MP3.

    Args:
        script_path: Path to a (preferably dramatized) script.
        mode: ``"deep_dive"``, ``"newsletter"`` or ``"basics"``; only affects
            the output filename.

    Returns:
        Path to the final MP3, or ``None`` if the script could not be read or
        the TTS call failed. The error is printed rather than raised so that
        the intermediate files already written stay available for inspection.
    """
    print("\nStarting podcast production (2 voices)...")

    if not Path(script_path).exists():
        print(f"Script file not found: {script_path}")
        return None

    try:
        dialogue_blocks = load_script_blocks(script_path)
    except ValueError as error:
        print(f"Error processing script: {error}")
        return None

    if not dialogue_blocks:
        print("Script is empty.")
        return None

    # The TTS model routes each line to a voice by the "Speaker: text" prefix,
    # and those names must match the speaker_voice_configs below exactly.
    conversation_text = "\n".join(
        f"{'Tony' if 'Host' in block['name'] else 'Gabriela'}: {block['text']}"
        for block in dialogue_blocks
    )

    print(f"Generating audio for {len(dialogue_blocks)} dialogue blocks...")

    try:
        client = genai.Client(
            api_key=config.require("GOOGLE_API_KEY"),
            http_options={"timeout": TTS_TIMEOUT_MS},
        )
        response = client.models.generate_content(
            model=TTS_MODEL,
            contents=f"{VOICE_DIRECTION}{conversation_text}",
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                        speaker_voice_configs=[
                            types.SpeakerVoiceConfig(
                                speaker=speaker,
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_name
                                    )
                                ),
                            )
                            for speaker, voice_name in SPEAKER_VOICES.items()
                        ]
                    )
                ),
            ),
        )

        if not (response.candidates and response.candidates[0].content.parts):
            print("API did not return audio.")
            return None

        pcm_data = response.candidates[0].content.parts[0].inline_data.data

        output_dir = config.episode_output_dir()
        # The unmixed voice track is kept so the mix can be redone without
        # paying for synthesis again.
        wav_path = output_dir / "podcast_raw.wav"
        write_wav_file(wav_path, pcm_data)

        episode = _mix_episode(AudioSegment.from_wav(wav_path) + VOICE_GAIN_DB)

        final_path = output_dir / OUTPUT_FILENAMES.get(mode, OUTPUT_FILENAMES["deep_dive"])
        episode.export(final_path, format="mp3")

        print(f"Final podcast generated: {final_path}")
        return str(final_path)

    except Exception as error:
        print(f"Critical error: {error}")
        return None
