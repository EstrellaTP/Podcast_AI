"""Sourcing stage of the pipeline: find AI news stories via the Perplexity API.

Two entry points, one per episode format:

* :func:`get_ai_news_summary` - Deep Dive. Anchors the episode on a single
  high-impact story and returns a prose summary plus its sources.
* :func:`run_newsletter_news_finder` - Newsletter. Returns exactly five stories
  as structured records.

Both record what they covered in ``data/recent_topics.json`` so later runs can
ask Perplexity to avoid repeating a story. That history is the only piece of
state the pipeline carries between executions.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import requests

from src import config

CONFIG = config.load_podcast_config()
API_URL = CONFIG["perplexity"]["api_url"]
MODEL = CONFIG["perplexity"]["model"]

# How many previously covered topics and URLs to send back to the model. The
# avoid-list is capped because the history grows without bound, and a long list
# starts crowding out the actual instructions in the prompt.
MAX_AVOID_ENTRIES = 8

BLOCKED_DOMAINS = ("youtube.com", "youtu.be")


def _request_headers() -> Dict[str, str]:
    """Build the Perplexity auth headers, resolving the key at call time."""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.require('PERPLEXITY_API_KEY')}",
    }


def load_recent_topics(
    history_path: Path = config.TOPIC_HISTORY_PATH,
    exclude_type: str | None = None,
) -> Tuple[Set[str], Set[str], Dict[str, Any]]:
    """Load previously covered topics and source URLs.

    Args:
        history_path: Path to the topic history file.
        exclude_type: Entry type to ignore. Deep Dive passes ``"newsletter"``
            so that a story mentioned in passing during a five-item bulletin
            does not disqualify it as a full Deep Dive subject later.

    Returns:
        ``(topics, primary_urls, raw_history)``. Topics and URLs are lowercased
        for case-insensitive comparison; the raw history is returned so callers
        can write it back without re-reading the file.
    """
    if not history_path.exists():
        return set(), set(), {"topics": [], "entries": []}

    try:
        with open(history_path, "r", encoding="utf-8") as history_file:
            history = json.load(history_file)
    except (json.JSONDecodeError, OSError):
        # A corrupt history should degrade into "no history", never abort a run.
        return set(), set(), {"topics": [], "entries": []}

    topics = {t.lower() for t in history.get("topics", []) if isinstance(t, str)}
    urls: Set[str] = set()

    for entry in history.get("entries", []):
        if not isinstance(entry, dict):
            continue
        if exclude_type and entry.get("type") == exclude_type:
            continue
        topic = entry.get("topic")
        url = entry.get("primary_url")
        if isinstance(topic, str) and topic.strip():
            topics.add(topic.lower())
        if isinstance(url, str) and url.strip():
            urls.add(url.lower())

    return topics, urls, history


def update_recent_topics_history(
    topic: str,
    primary_url: str | None,
    history_path: Path = config.TOPIC_HISTORY_PATH,
    existing_history: Dict[str, Any] | None = None,
    entry_type: str = "deep_dive",
) -> None:
    """Record a covered story in the topic history.

    Each entry stores both the headline and the primary source URL. The URL is
    the stronger signal of the two: outlets reword the same story, so two
    different headlines pointing at one article are the same episode subject.

    Args:
        topic: Headline to record.
        primary_url: URL of the anchor source, if any.
        history_path: Path to the history file.
        existing_history: History already held in memory, to avoid a second read.
        entry_type: ``"deep_dive"`` or ``"newsletter"``.
    """
    history: Dict[str, Any] = {"topics": [], "entries": []}
    if existing_history is not None:
        history = existing_history
    elif history_path.exists():
        try:
            with open(history_path, "r", encoding="utf-8") as history_file:
                history = json.load(history_file)
        except (json.JSONDecodeError, OSError):
            history = {"topics": [], "entries": []}

    history.setdefault("topics", [])
    history.setdefault("entries", [])

    seen_topics = {t.lower() for t in history["topics"] if isinstance(t, str)}
    if topic and topic.strip() and topic.lower() not in seen_topics:
        history["topics"].append(topic)

    entries = [entry for entry in history.get("entries", []) if isinstance(entry, dict)]
    existing_keys = {
        (entry.get("topic", "").lower(), entry.get("primary_url", "").lower())
        for entry in entries
    }

    key = (topic.lower() if topic else "", (primary_url or "").lower())
    if key not in existing_keys and (topic or primary_url):
        entries.append(
            {
                "topic": topic,
                "primary_url": primary_url or "",
                "captured_at": datetime.now().isoformat(),
                "type": entry_type,
            }
        )

    history["entries"] = entries
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def call_perplexity(
    recent_topics: Set[str] | None = None,
    recent_urls: Set[str] | None = None,
) -> Dict[str, Any]:
    """Ask Perplexity for one recent, high-impact AI story.

    Args:
        recent_topics: Headlines already covered, to be avoided.
        recent_urls: Source URLs already used, to be avoided.

    Returns:
        The raw API response, including the ``search_results`` block that
        carries the citations.
    """
    avoid_topics = sorted(recent_topics or set())[:MAX_AVOID_ENTRIES]
    avoid_urls = sorted(recent_urls or set())[:MAX_AVOID_ENTRIES]

    prompt = CONFIG["prompts"]["news_finder"]
    user_message = prompt["user_template"].format(
        avoid_topics_block="\n".join(f"- {t}" for t in avoid_topics) or "- none recorded",
        avoid_urls_block="\n".join(f"- {u}" for u in avoid_urls) or "- none recorded",
    )

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": 2000,
        # Low temperature: this stage reports facts. The creative latitude
        # belongs downstream, in the script generator and the dramatizer.
        "temperature": 0.3,
    }

    response = requests.post(API_URL, headers=_request_headers(), json=payload)
    response.raise_for_status()
    return response.json()


def prune_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Drop sources the podcast cannot cite on air, such as video platforms."""
    return [
        source
        for source in sources
        if source.get("url")
        and not any(blocked in source["url"].lower() for blocked in BLOCKED_DOMAINS)
    ]


def extract_summary_and_sources(
    response: Dict[str, Any],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Split a Perplexity response into its prose answer and its citations."""
    choices = response.get("choices", [])
    if not choices:
        raise ValueError("Perplexity response has no 'choices'")

    summary = (choices[0].get("message", {}).get("content") or "").strip()

    sources: List[Dict[str, Any]] = []
    for item in response.get("search_results", []) or []:
        # Citations normally arrive as objects, but the API has also returned
        # bare URL strings, so both shapes are accepted.
        if isinstance(item, dict):
            url = item.get("url") or ""
            title = item.get("title") or url
            date = item.get("date")
        else:
            url = str(item)
            title = url
            date = None

        if url:
            sources.append({"title": title, "url": url, "date": date})

    return summary, prune_sources(sources)


def extract_topics_from_summary(summary: str) -> List[str]:
    """Pull up to two topic headings out of the model's prose answer.

    The prompt asks for a ``Primary topic:`` line, but the model sometimes
    answers with Markdown headings or with a "themes chosen" list instead, so
    all three shapes are scanned before settling for whatever was found.
    """
    topics: List[str] = []

    for line in summary.splitlines():
        lowered = line.lower()
        if lowered.startswith("primary topic") or lowered.startswith("tema principal"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                topics.append(parts[1].strip())
                continue

        heading = re.match(r"^##\s+\d*\.?\s*(.+)", line.strip())
        if heading:
            topics.append(heading.group(1).strip())

    collecting = False
    for line in summary.splitlines():
        if "themes chosen" in line.lower():
            collecting = True
            continue
        if collecting:
            if line.strip().startswith("-"):
                topics.append(line.strip("- ").strip())
            elif not line.strip():
                break

    seen: Set[str] = set()
    unique_topics = []
    for topic in topics:
        if topic.lower() not in seen:
            seen.add(topic.lower())
            unique_topics.append(topic)

    return unique_topics[:2]


def save_news_summary(
    summary: str,
    sources: List[Dict[str, Any]],
    raw_response: Dict[str, Any],
    topics: List[str],
    prefix: str = "ai_news",
) -> str:
    """Persist the research output for the script generator to pick up.

    The raw API response is kept alongside the parsed fields so that a bad
    script can be traced back to what the model actually returned.

    Returns:
        Path to the written JSON file.
    """
    output_dir = config.episode_output_dir()
    file_path = output_dir / f"{prefix}_summary_{datetime.now():%Y-%m-%d}.json"

    payload = {
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "sources": sources,
        "topics": topics,
        "raw_response": raw_response,
    }

    with open(file_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)

    return str(file_path)


def get_ai_news_summary() -> Dict[str, Any]:
    """Run the Deep Dive research stage end to end.

    Calls Perplexity while avoiding previously covered stories, extracts the
    summary, sources and topics, saves them to disk, and records the anchor
    story in the history.

    Returns:
        Dict with ``summary``, ``sources``, ``topics`` and ``file``.
    """
    history_topics, history_urls, history = load_recent_topics(exclude_type="newsletter")

    response = call_perplexity(recent_topics=history_topics, recent_urls=history_urls)
    summary, sources = extract_summary_and_sources(response)
    topics = extract_topics_from_summary(summary)
    file_path = save_news_summary(summary, sources, response, topics, prefix="ai_news")

    try:
        update_recent_topics_history(
            topics[0] if topics else "",
            sources[0]["url"] if sources else "",
            existing_history=history,
            entry_type="deep_dive",
        )
    except OSError as error:
        # Losing the de-duplication record is not worth discarding a finished
        # research run, so this is reported and swallowed.
        print(f"Warning: could not update recent topics: {error}")

    return {
        "summary": summary,
        "sources": sources,
        "topics": topics,
        "file": file_path,
    }


def call_perplexity_newsletter() -> Dict[str, Any]:
    """Ask Perplexity for exactly five recent AI stories, returned as JSON."""
    prompt = CONFIG["prompts"]["news_finder_newsletter"]

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user_template"]},
        ],
        "max_tokens": 2000,
        "temperature": 0.3,
    }

    response = requests.post(API_URL, headers=_request_headers(), json=payload)
    response.raise_for_status()
    return response.json()


def parse_newsletter_response(response: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract the list of news items from a newsletter response.

    Args:
        response: Raw Perplexity API response.

    Returns:
        One dict per story, with keys ``title``, ``summary``, ``source``,
        ``url`` and ``date``.

    Raises:
        ValueError: if the response is empty or is not the requested JSON array.
    """
    choices = response.get("choices", [])
    if not choices:
        raise ValueError("Perplexity response has no 'choices'")

    content = (choices[0].get("message", {}).get("content") or "").strip()

    # The prompt forbids Markdown, but the model still wraps the array in a
    # fenced block often enough that unwrapping it is cheaper than retrying.
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("\n", 1)[0]

    try:
        news_items = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Failed to parse newsletter JSON from Perplexity: {error}\n"
            f"Content: {content}"
        ) from error

    if not isinstance(news_items, list):
        raise ValueError("Expected a JSON array of news items, got an object")

    return news_items


def run_newsletter_news_finder() -> Tuple[str, List[Dict[str, str]]]:
    """Run the Newsletter research stage end to end.

    Returns:
        ``(path to the saved JSON file, list of news items)``.
    """
    response = call_perplexity_newsletter()
    news_items = parse_newsletter_response(response)

    output_dir = config.episode_output_dir()
    file_path = output_dir / f"newsletter_summary_{datetime.now():%Y-%m-%d}.json"

    with open(file_path, "w", encoding="utf-8") as output_file:
        json.dump(
            {
                "generated_at": datetime.now().isoformat(),
                "news_items": news_items,
                "count": len(news_items),
            },
            output_file,
            ensure_ascii=False,
            indent=2,
        )

    # Every headline in the bulletin is recorded, so a later Deep Dive can tell
    # which stories the show has already mentioned.
    for item in news_items:
        try:
            update_recent_topics_history(
                item.get("title", ""), item.get("url", ""), entry_type="newsletter"
            )
        except OSError as error:
            print(f"Warning: could not record newsletter item: {error}")

    return str(file_path), news_items


if __name__ == "__main__":
    result = get_ai_news_summary()

    print("\n=== SUMMARY (truncated preview) ===\n")
    print(result["summary"][:1500], "...\n")

    print("=== SOURCES ===")
    for index, source in enumerate(result["sources"], start=1):
        print(
            f"{index}. {source.get('title')} - {source.get('url')} "
            f"(date: {source.get('date')})"
        )

    print(f"\nSaved full data to: {result['file']}")
