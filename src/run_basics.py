"""Basics pipeline: an educational episode built from a topic and key points.

Unlike the other two formats there is no research stage: the content comes
from the caller (the REST API) or from ``basics_episode`` in the config file.

    python -m src.run_basics
"""

from typing import List, Optional

from src import config
from src.audio_generator import generate_podcast
from src.dramatizer import dramatize_script
from src.script_generator import run_basics

DEFAULT_EPISODE = config.load_podcast_config().get("basics_episode", {})


def run_basics_pipeline(
    topic: Optional[str] = None, points: Optional[List[str]] = None
) -> str:
    """Run script -> dramatization -> audio for a Basics episode.

    Args:
        topic: Episode topic. Defaults to ``basics_episode.topic`` in the config.
        points: Key points to cover. Defaults to ``basics_episode.points``.

    Returns:
        Path to the final MP3.

    Raises:
        RuntimeError: if audio generation fails. Raised here, rather than
            returning ``None``, because the API needs the file to upload it.
    """
    topic = topic if topic is not None else DEFAULT_EPISODE.get("topic", "AI Basics")
    points = points if points is not None else DEFAULT_EPISODE.get("points", [])

    print("--- Starting 'Basics' Pipeline ---")

    print(f"1. Generating script for topic: '{topic}'...")
    script_path = run_basics(topic=topic, key_points=points)
    print(f"   -> Script saved at: {script_path}")

    print("2. Dramatizing the script...")
    dramatized_script_path = dramatize_script(script_path)
    print(f"   -> Dramatized script saved at: {dramatized_script_path}")

    print("3. Generating podcast audio...")
    final_audio_path = generate_podcast(dramatized_script_path, mode="basics")
    if not final_audio_path:
        raise RuntimeError("Audio generation failed; see the log above for the cause.")

    print("\n--- 'Basics' Episode Pipeline Completed ---")
    print(f"The final podcast is available at: {final_audio_path}")
    return final_audio_path


if __name__ == "__main__":
    run_basics_pipeline()
