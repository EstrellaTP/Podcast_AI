"""REST API: produce a Basics episode on demand and publish it to Supabase.

``POST /produce`` runs the full Basics pipeline synchronously, uploads the MP3
to Supabase Storage and tracks the job in the ``podcasts_history`` table, so a
frontend can list past episodes and their status.

Run with:

    uvicorn src.api:app --reload
"""

import hmac
import os
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from supabase import Client, create_client

from src import config
from src.run_basics import run_basics_pipeline

# Must match the bucket name in the Supabase project. Uploads and public-URL
# lookups both read it from here: they previously used "podcast" and "podcasts"
# respectively. Only the upload is a network call (get_public_url just formats
# a string), so "podcast" is the bucket that actually exists, and every link
# the API returned pointed at a bucket with nothing in it.
STORAGE_BUCKET = "podcast"
HISTORY_TABLE = "podcasts_history"

# Fail at startup rather than on the first request: a missing auth token must
# never leave the endpoint open, and missing Supabase credentials would
# otherwise surface only after a paid pipeline run had already finished.
API_AUTH_TOKEN = config.require("API_AUTH_TOKEN")
supabase: Client = create_client(config.require("SUPABASE_URL"), config.require("SUPABASE_KEY"))

app = FastAPI(title="AI Podcast Generator")


class PodcastRequest(BaseModel):
    """Body of ``POST /produce``.

    The JSON field names stay in Spanish (``tema``, ``puntos``) through aliases,
    because they are the published contract that existing clients already send.
    """

    model_config = ConfigDict(populate_by_name=True)

    topic: str = Field(alias="tema")
    key_points: List[str] = Field(alias="puntos")


@app.post("/produce")
async def produce_podcast(
    request: PodcastRequest, x_token: Optional[str] = Header(None)
) -> dict:
    """Generate a Basics episode, upload it, and return its public URL.

    The job is recorded as ``processing`` before the pipeline starts and moved
    to ``completed`` or ``error`` afterwards, so an episode that fails midway
    is still visible to the frontend instead of silently disappearing.

    Headers:
        x-token: Must equal the ``API_AUTH_TOKEN`` environment variable.

    Raises:
        HTTPException: 401 on a bad token, 500 if any pipeline step fails.
    """
    # Constant-time comparison, so response timing leaks nothing about the token.
    if not x_token or not hmac.compare_digest(x_token, API_AUTH_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid token")

    podcast_id = None
    try:
        # Column names are the database schema and are kept as-is.
        insert_result = (
            supabase.table(HISTORY_TABLE)
            .insert({"tema": request.topic, "estado": "processing"})
            .execute()
        )
        podcast_id = insert_result.data[0]["id"]

        local_audio_path = run_basics_pipeline(topic=request.topic, points=request.key_points)

        # Prefixing with the row id keeps episodes generated on the same day
        # (which share a filename) from overwriting each other in the bucket.
        storage_path = f"episodios/{podcast_id}_{os.path.basename(local_audio_path)}"

        with open(local_audio_path, "rb") as audio_file:
            supabase.storage.from_(STORAGE_BUCKET).upload(
                file=audio_file,
                path=storage_path,
                file_options={"content-type": "audio/mpeg"},
            )

        public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)

        supabase.table(HISTORY_TABLE).update(
            {"estado": "completed", "audio_url": public_url}
        ).eq("id", podcast_id).execute()

        return {
            "status": "success",
            "message": "Podcast generated and uploaded to the cloud",
            "audio_url": public_url,
        }

    except Exception as error:
        if podcast_id is not None:
            supabase.table(HISTORY_TABLE).update({"estado": "error"}).eq(
                "id", podcast_id
            ).execute()
        raise HTTPException(status_code=500, detail=str(error)) from error
