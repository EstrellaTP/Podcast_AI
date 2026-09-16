"""Central configuration for the podcast pipeline.

Every module imports its paths and credentials from here instead of calling
``load_dotenv()`` and ``os.getenv()`` on its own. That matters because the old
layout read the keys at import time in some modules but loaded ``.env`` in
others, so whether a key was populated depended on the order of the imports in
the orchestrator -- a silent failure that surfaced as a 401 from the provider.
Loading the environment here, once, removes that coupling.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# --- Paths -----------------------------------------------------------------
# Anchored on this file rather than the working directory, so the pipelines
# behave the same whether they are launched from the repo root or from src/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
PODCAST_CONFIG_PATH = PROJECT_ROOT / "config" / "podcast_config.json"
TOPIC_HISTORY_PATH = DATA_DIR / "recent_topics.json"

# --- Credentials -----------------------------------------------------------
load_dotenv(PROJECT_ROOT / ".env")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def require(name: str) -> str:
    """Return the environment variable ``name`` or fail with a usable message.

    Credentials are validated at the point of use rather than at import time:
    the standalone pipelines need the Google and Perplexity keys but no
    Supabase project, so importing a module should never demand a key that
    its caller will not use.

    Raises:
        RuntimeError: if the variable is unset or empty.
    """
    value = globals().get(name) or os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable {name!r}. "
            "Copy .env.example to .env and fill it in."
        )
    return value


def load_podcast_config() -> Dict[str, Any]:
    """Load config/podcast_config.json (prompts, voice panning, defaults)."""
    with open(PODCAST_CONFIG_PATH, "r", encoding="utf-8") as config_file:
        return json.load(config_file)


def episode_output_dir(when: Optional[datetime] = None) -> Path:
    """Return (and create) the output directory for a given day.

    Episodes are grouped as ``output/YYYY_MM_DD/`` so that a day's script,
    raw audio and final mix stay together.
    """
    when = when or datetime.now()
    directory = OUTPUT_DIR / when.strftime("%Y_%m_%d")
    directory.mkdir(parents=True, exist_ok=True)
    return directory
