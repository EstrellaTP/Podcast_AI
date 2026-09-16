"""Deep Dive pipeline: one in-depth episode about a single recent AI story.

    python -m src.run_deep_dive
"""

from src.audio_generator import generate_podcast
from src.dramatizer import dramatize_script
from src.news_finder import get_ai_news_summary
from src.script_generator import run_from_json

PREVIEW_LINES = 20


def main() -> None:
    """Run research -> script -> dramatization -> audio for a Deep Dive episode."""
    news = get_ai_news_summary()
    summary_path = news.get("file")
    if not summary_path:
        raise RuntimeError("news_finder did not return the generated JSON path.")

    script_path, script_text = run_from_json(summary_path)

    print(f"Summary generated at: {summary_path}")
    print(f"Script generated at: {script_path}\n")
    print("Preview (first lines):\n")
    print("\n".join(script_text.splitlines()[:PREVIEW_LINES]))

    print("\n--- Dramatizing Script ---")
    dramatized_script_path = dramatize_script(script_path)

    print("\n--- Generating Podcast Audio ---")
    generate_podcast(dramatized_script_path, mode="deep_dive")


if __name__ == "__main__":
    main()
