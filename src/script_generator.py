"""Scriptwriting stage of the pipeline: turn research into a two-voice dialogue.

The model is asked to write plain lines labelled ``Voz A:`` / ``Voz B:``
rather than JSON. Free text gives noticeably more natural dialogue at this
stage, and the labels are enough to recover the structure afterwards in
:func:`script_to_blocks`. The resulting blocks are what the dramatizer and the
audio generator consume.

This module also owns the on-disk script format, so :func:`load_script_blocks`
lives here as the single reader shared by every later stage.
"""

import ast
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import requests

from src import config

CONFIG = config.load_podcast_config()
API_URL = CONFIG["perplexity"]["api_url"]
MODEL = CONFIG["perplexity"]["model"]

# Name of the variable in the script file, e.g. ``podcast_script = [...]``.
SCRIPT_VARIABLE_NAME = "podcast_script"

# Maps the speaker labels the prompts ask the model to emit (Spanish, because
# the episode itself is in Spanish) to the internal role and the character.
# ``name`` is what the audio generator uses to pick the TTS voice; ``voice_id``
# is the character name the dramatizer sees, so it can keep each tone distinct.
VOICE_ROLES: Dict[str, Dict[str, str]] = {
    "voz a": {"name": "Host", "voice_id": "Tony"},
    "voz b": {"name": "Guest_1", "voice_id": "Gabriela"},
}

BLOCKED_DOMAINS = ("youtube.com", "youtu.be")


# --- Script file I/O ---------------------------------------------------------

def load_script_blocks(script_path: str | Path) -> List[Dict[str, str]]:
    """Read a dialogue script from disk.

    Accepted formats:

    * A JSON list of blocks, or a JSON object wrapping one under
      ``podcast_script`` (or the legacy key ``podcast_scpt``).
    * A Python-style assignment, ``podcast_script = [...]``, which is what this
      pipeline writes and what hand-written test scripts tend to use.

    The assignment is parsed as a literal with :func:`ast.literal_eval`, never
    executed. Earlier versions ran these files through ``exec()``, which would
    execute arbitrary code from any script placed in the output folder.

    Returns:
        The list of ``{"name", "voice_id", "text"}`` blocks, or an empty list if
        the file holds no dialogue.

    Raises:
        ValueError: if the file cannot be parsed as either format.
    """
    content = Path(script_path).read_text(encoding="utf-8").strip()

    try:
        parsed: Any = json.loads(content)
    except json.JSONDecodeError:
        # Assignment format: discard everything up to the first "=". Dialogue
        # text may contain "=" too, but it always comes after the variable name.
        _, _, literal = content.partition("=")
        try:
            parsed = json.loads(literal)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(literal.strip())
            except (ValueError, SyntaxError) as error:
                raise ValueError(f"Unreadable script file {script_path}: {error}") from error

    if isinstance(parsed, dict):
        parsed = parsed.get("podcast_script") or parsed.get("podcast_scpt", [])

    return parsed if isinstance(parsed, list) else []


def format_script_file(blocks: List[Dict[str, str]]) -> str:
    """Serialize dialogue blocks into the on-disk script format."""
    return f"{SCRIPT_VARIABLE_NAME} = " + json.dumps(blocks, ensure_ascii=False, indent=2)


def save_podcast_script(script_text: str, prefix: str = "podcast_script") -> str:
    """Write a script into today's output folder.

    Args:
        script_text: Serialized script, as produced by :func:`format_script_file`.
        prefix: Filename prefix; the newsletter uses ``podcast_script_newsletter``.

    Returns:
        Path to the written file.
    """
    output_dir = config.episode_output_dir()
    file_path = output_dir / f"{prefix}_{datetime.now():%Y-%m-%d}.txt"
    file_path.write_text(script_text, encoding="utf-8")
    return str(file_path)


# --- Research input ----------------------------------------------------------

def load_news_summary(path: str) -> Tuple[str, Dict[str, Any]]:
    """Load a research file written by the news finder.

    Returns:
        ``(summary_text, full_data)``. If the file has no ``summary`` field the
        whole document is serialized and used as the summary, so the model
        still gets the raw material.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as summary_file:
        data = json.load(summary_file)
    summary_text = data.get("summary") or json.dumps(data, ensure_ascii=False, indent=2)
    return summary_text, data


def find_latest_news_summary() -> str:
    """Return the most recently written Deep Dive research file."""
    candidates = sorted(
        config.OUTPUT_DIR.glob("**/ai_news_summary_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No summary found in {config.OUTPUT_DIR}")
    return str(candidates[0])


def sanitize_sources(sources: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Keep only citable sources, reduced to the fields the prompt uses."""
    clean_sources = []
    for source in sources or []:
        url = source.get("url") or ""
        if not url or any(blocked in url.lower() for blocked in BLOCKED_DOMAINS):
            continue
        clean_sources.append({"title": source.get("title") or url, "url": url})
    return clean_sources


def extract_topics(summary_text: str, full_data: Dict[str, Any]) -> List[str]:
    """Collect candidate episode topics, preferring those the news finder saved.

    Returns:
        Up to two unique topics, in order of preference.
    """
    topics: List[str] = list(full_data.get("topics", [])) if isinstance(full_data, dict) else []

    for line in summary_text.splitlines():
        heading = re.match(r"^##\s+\d*\.?\s*(.+)", line.strip())
        if heading:
            topics.append(heading.group(1).strip())

    seen: Set[str] = set()
    unique_topics = []
    for topic in topics:
        if topic.lower() not in seen:
            seen.add(topic.lower())
            unique_topics.append(topic)
    return unique_topics[:2]


# --- Topic history -----------------------------------------------------------

def load_recent_topics(history_path: Path) -> Set[str]:
    """Return the lowercased set of topics already covered."""
    if not history_path.exists():
        return set()
    try:
        with open(history_path, "r", encoding="utf-8") as history_file:
            history = json.load(history_file)
    except (json.JSONDecodeError, OSError):
        return set()
    return {t.lower() for t in history.get("topics", []) if isinstance(t, str)}


def update_recent_topics(history_path: Path, topics: List[str]) -> None:
    """Append newly covered topics to the history file."""
    history: Dict[str, Any] = {"topics": [], "entries": []}
    if history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as history_file:
                history = json.load(history_file)
        except (json.JSONDecodeError, OSError):
            pass

    history.setdefault("topics", [])
    history.setdefault("entries", [])
    timestamp = datetime.now().isoformat()
    seen = {t.lower() for t in history["topics"]}

    for topic in topics:
        if topic.lower() not in seen:
            history["topics"].append(topic)
            seen.add(topic.lower())
            history["entries"].append({"topic": topic, "captured_at": timestamp})

    history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(history_path, "w", encoding="utf-8") as history_file:
        json.dump(history, history_file, ensure_ascii=False, indent=2)


def pick_fresh_topics(candidates: List[str], history: Set[str], limit: int = 2) -> List[str]:
    """Prefer topics not covered before.

    If every candidate has been covered, the candidates are used anyway: by this
    point the research has already been paid for, and a repeated angle is a
    better outcome than aborting the episode.
    """
    fresh = [topic for topic in candidates if topic.lower() not in history]
    return fresh[:limit] if fresh else candidates[:limit]


# --- Generation --------------------------------------------------------------

def generate_podcast_script(
    summary_text: str,
    topics: List[str],
    sources: List[Dict[str, str]],
    mode: str = "deep_dive",
) -> str:
    """Ask Perplexity to write the raw dialogue for an episode.

    The three formats share one call but differ in prompt and inputs, so
    ``summary_text`` carries a different payload depending on ``mode``:

    * ``"deep_dive"``: the research summary.
    * ``"basics"``: the bullet list of key points to teach.
    * ``"newsletter"``: the five news items, serialized as JSON.

    Returns:
        The raw ``Voz A:`` / ``Voz B:`` script, or ``""`` if the response is
        malformed (surfaced by :func:`script_to_blocks` as a format error).
    """
    if mode == "basics":
        prompt = CONFIG["prompts"]["script_generator_basics"]
        user_message = prompt["user_template"].format(TOPIC=topics[0], KEY_POINTS=summary_text)
    elif mode == "newsletter":
        prompt = CONFIG["prompts"]["script_generator_newsletter"]
        user_message = prompt["user_template"].format(news_json=summary_text)
    else:
        prompt = CONFIG["prompts"]["script_generator"]
        user_message = prompt["user_template"].format(
            topics_text="\n".join(f"- {topic}" for topic in topics),
            summary_text=summary_text,
            sources_text="\n".join(f"- {source['title']}" for source in sources),
        )

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.require('PERPLEXITY_API_KEY')}",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 2000,
        # Higher than the research stage: here some variety in phrasing is wanted.
        "temperature": 0.7,
    }

    response = requests.post(API_URL, headers=headers, json=payload)
    response.raise_for_status()
    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, ValueError):
        return ""


def script_to_blocks(script_text: str) -> List[Dict[str, str]]:
    """Parse ``Voz A:`` / ``Voz B:`` lines into structured dialogue blocks.

    Lines without a recognised speaker label are dropped. That filter is
    deliberate: models add titles, stage directions or a stray third speaker
    despite the prompt, and any of those would otherwise be read aloud.

    Raises:
        RuntimeError: if no labelled line is found at all.
    """
    blocks = []
    for line in script_text.splitlines():
        if ":" not in line:
            continue
        label, text = (part.strip() for part in line.split(":", 1))
        role = VOICE_ROLES.get(label.lower())
        if role and text:
            blocks.append({"name": role["name"], "voice_id": role["voice_id"], "text": text})

    if not blocks:
        raise RuntimeError("Generated script does not use the 'Voz A:' / 'Voz B:' format.")
    return blocks


# --- Per-format entry points -------------------------------------------------

def run_from_json(json_path: str) -> Tuple[str, str]:
    """Write a Deep Dive script from a research file.

    Returns:
        ``(path to the saved script, script content)``.
    """
    summary, data = load_news_summary(json_path)
    history_path = config.TOPIC_HISTORY_PATH
    topics = pick_fresh_topics(extract_topics(summary, data), load_recent_topics(history_path))
    sources = sanitize_sources(data.get("sources", []))

    raw_script = generate_podcast_script(summary, topics, sources, mode="deep_dive")
    script_text = format_script_file(script_to_blocks(raw_script))

    script_path = save_podcast_script(script_text)
    update_recent_topics(history_path, topics)
    return script_path, script_text


def run_basics(topic: str, key_points: List[str]) -> str:
    """Write a Basics (educational) script from a topic and its key points.

    Returns:
        Path to the saved script.
    """
    key_points_text = "\n".join(f"- {point}" for point in key_points)
    raw_script = generate_podcast_script(
        summary_text=key_points_text, topics=[topic], sources=[], mode="basics"
    )
    script_text = format_script_file(script_to_blocks(raw_script))
    return save_podcast_script(script_text)


def run_newsletter(news_items: List[Dict[str, str]]) -> Tuple[str, str]:
    """Write a Newsletter script covering a list of news items.

    Args:
        news_items: Stories with keys ``title``, ``summary``, ``source``,
            ``url`` and ``date``.

    Returns:
        ``(path to the saved script, script content)``.
    """
    news_json = json.dumps(news_items, ensure_ascii=False, indent=2)
    raw_script = generate_podcast_script(
        summary_text=news_json, topics=[], sources=[], mode="newsletter"
    )
    script_text = format_script_file(script_to_blocks(raw_script))
    script_path = save_podcast_script(script_text, prefix="podcast_script_newsletter")
    return script_path, script_text


def main() -> None:
    """CLI entry point: script the research file in ``NEWS_JSON_PATH``, or the latest one."""
    try:
        json_path = os.getenv("NEWS_JSON_PATH") or find_latest_news_summary()
        script_path, _ = run_from_json(json_path)
        print(f"Script OK: {script_path}")
    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()
