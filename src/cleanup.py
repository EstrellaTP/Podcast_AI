"""Maintenance script: forget the stories recorded in today's topic history.

The news finder refuses to repeat a story it has already recorded, so a failed
or discarded run still "uses up" the stories it found. Run this after a bad
test run to make today's stories eligible again:

    python -m src.cleanup
"""

import json
from datetime import datetime

from src import config


def remove_todays_entries() -> None:
    """Delete every history entry captured today and rebuild the topic list."""
    history_path = config.TOPIC_HISTORY_PATH
    if not history_path.exists():
        print(f"File not found at: {history_path}")
        return

    with open(history_path, "r", encoding="utf-8") as history_file:
        history = json.load(history_file)

    today = datetime.now().strftime("%Y-%m-%d")
    entries = history.get("entries", [])

    # captured_at is an ISO timestamp, so a date-prefix match selects today.
    kept_entries = [
        entry for entry in entries if not entry.get("captured_at", "").startswith(today)
    ]
    removed_count = len(entries) - len(kept_entries)

    # "topics" is derived from the entries, so it is rebuilt rather than filtered;
    # otherwise a removed story would still be blocked through the topic list.
    history["entries"] = kept_entries
    history["topics"] = list({entry["topic"] for entry in kept_entries if "topic" in entry})

    with open(history_path, "w", encoding="utf-8") as history_file:
        json.dump(history, history_file, ensure_ascii=False, indent=2)

    if removed_count:
        print(f"Cleanup completed. Removed {removed_count} records from today ({today}).")
    else:
        print(f"History is clean. No records from today ({today}) were found.")


if __name__ == "__main__":
    remove_todays_entries()
