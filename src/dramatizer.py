"""Dramatization stage: make a written script sound like spoken conversation.

LLM-written dialogue reads well but sounds stiff when synthesized: long
monologues, no hesitation, nobody reacting. Rather than asking the script
generator to do everything at once, a second, dedicated pass rewrites the text
with fillers and pauses, and splits long turns by inserting short listener
reactions ("ajá", "claro") as new turns. Keeping this separate lets each prompt
stay focused, and a failure here costs only naturalness, not the episode.
"""

import json
from pathlib import Path

from google import genai
from google.genai import types

from src import config
from src.script_generator import format_script_file, load_script_blocks

MODEL = "gemini-3-flash-preview"

# Filled with str.format(), so the JSON braces in the example are doubled.
DRAMATIZATION_PROMPT = """
    Act as a professional script editor and voice director for a podcast.
    I will provide a JSON list of dialogue turns. The current text is too written/robotic.

    YOUR TASK:
    Rewrite the 'text' field for each turn to make it sound like a NATURAL SPANISH (Madrid) CONVERSATION.
    CRITICAL: You must BREAK UP long monologues by inserting SHORT reactions (interjections/phatic functions) from the listener as NEW DIALOGUE TURNS.

    GUIDELINES:
    1. **Disfluencies**: Add natural fillers like "eh...", "mmm...", "bueno...", "a ver...", "o sea...". Avoid repetition.
    2. **Pacing**: Use punctuation (...) to indicate pauses.
    3. **Tone**:
       - **Tony (Host)**: Energetic, curious, enthusiastic.
       - **Gabriela (Expert)**: Calm, thoughtful, articulate.
    4. **Interjections/Backchanneling (MANDATORY)**:
       - If a turn is too long or you feel requires some phatic function from the counterparty, add the backchannel or interjection.
       - Insert a **NEW JSON OBJECT** for the listener to provide feedback.
       - Feedback examples: "mm-hmm", "ajá", "ya...", "claro", "entiendo", "vale", "mm-hmm".
       - This feedback must be assigned to the OTHER speaker.

    EXAMPLE OF DESIRED TRANSFORMATION:
    Input:
    [
      {{ "name": "Host", "voice_id": "Tony", "text": "AI agents are changing how we work. They can automate tasks and even write code. It's truly a revolution." }}
    ]

    Output:
    [
      {{ "name": "Host", "voice_id": "Tony", "text": "Los agentes de IA... bueno, están cambiando totalmente cómo trabajamos." }},
      {{ "name": "Guest_1", "voice_id": "Gabriela", "text": "Ajá..." }},
      {{ "name": "Host", "voice_id": "Tony", "text": "Pueden automatizar tareas, escribir código... Mira, es una auténtica revolución." }}
    ]

    OUTPUT FORMAT:
    Return strictly a JSON list of objects with the exact same schema (name, voice_id, text).
    Do not add markdown code blocks.

    INPUT:
    {blocks_json}
    """


def dramatize_script(script_path: str) -> str:
    """Rewrite a script for natural delivery and save it next to the original.

    Args:
        script_path: Path to a script produced by the script generator.

    Returns:
        Path to the ``*_dramatized.txt`` file on success. On any failure the
        **original** path is returned instead: a flat but correct episode is a
        better result than none, so the pipeline carries on with the undramatized
        script rather than aborting.
    """
    print(f"\nDramatizing script with {MODEL}... ({Path(script_path).name})")

    if not Path(script_path).exists():
        print(f"Script file not found: {script_path}")
        return script_path

    try:
        original_blocks = load_script_blocks(script_path)
    except ValueError as error:
        print(f"Error reading script: {error}")
        return script_path

    if not original_blocks:
        print("Script is empty.")
        return script_path

    prompt = DRAMATIZATION_PROMPT.format(
        blocks_json=json.dumps(original_blocks, ensure_ascii=False, indent=2)
    )

    try:
        client = genai.Client(api_key=config.require("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                # JSON mode keeps the output parseable without a repair step.
                response_mime_type="application/json",
                temperature=0.6,
            ),
        )

        dramatized_text = response.text.strip()
        # JSON mode should never emit a fenced block, but earlier model
        # versions did, and unwrapping it is harmless when it does not.
        if dramatized_text.startswith("```"):
            dramatized_text = dramatized_text.split("\n", 1)[1].rsplit("\n", 1)[0]

        dramatized_blocks = json.loads(dramatized_text)

        source = Path(script_path)
        dramatized_path = source.with_name(f"{source.stem}_dramatized{source.suffix}")
        dramatized_path.write_text(format_script_file(dramatized_blocks), encoding="utf-8")

        print(f"Dramatized script saved at: {dramatized_path}")
        return str(dramatized_path)

    except Exception as error:
        print(f"Error in dramatization, continuing with the original script: {error}")
        return script_path
