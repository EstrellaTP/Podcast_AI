"""Newsletter pipeline: a fast-paced bulletin covering five recent AI stories.

    python -m src.run_newsletter
"""

import sys
import time

from src.audio_generator import generate_podcast
from src.dramatizer import dramatize_script
from src.news_finder import run_newsletter_news_finder
from src.script_generator import run_newsletter

SEPARATOR = "=" * 60


def _print_step(title: str) -> None:
    print(f"\n{SEPARATOR}\n{title}\n{SEPARATOR}")


def run_newsletter_pipeline() -> str:
    """Run research -> script -> dramatization -> audio for a Newsletter episode.

    Returns:
        Path to the final MP3. The process exits with status 1 on failure, so
        a scheduler (e.g. cron) can detect a failed run.
    """
    start_time = time.time()

    try:
        _print_step("STEP 1: Fetching AI news for the newsletter...")
        news_path, news_items = run_newsletter_news_finder()
        print(f"News retrieved: {len(news_items)} items")
        print(f"File saved at: {news_path}")

        _print_step("STEP 2: Generating newsletter script...")
        script_path, _ = run_newsletter(news_items)
        print(f"Script saved at: {script_path}")

        _print_step("STEP 3: Dramatizing the script...")
        dramatized_script_path = dramatize_script(script_path)
        print(f"Dramatized script saved at: {dramatized_script_path}")

        _print_step("STEP 4: Generating podcast audio...")
        final_audio_path = generate_podcast(dramatized_script_path, mode="newsletter")
        if not final_audio_path:
            raise RuntimeError("generate_podcast() did not return a valid path")
        print(f"Final podcast saved at: {final_audio_path}")

        minutes, seconds = divmod(int(time.time() - start_time), 60)
        _print_step("NEWSLETTER PIPELINE COMPLETED SUCCESSFULLY")
        print(f"Total time: {minutes}m {seconds}s")
        print(f"Final podcast: {final_audio_path}")
        print(f"{SEPARATOR}\n")

        return final_audio_path

    except Exception as error:
        print(f"\nERROR in pipeline: {error}")
        print(f"Time until error: {time.time() - start_time:.1f}s")
        sys.exit(1)


if __name__ == "__main__":
    run_newsletter_pipeline()
