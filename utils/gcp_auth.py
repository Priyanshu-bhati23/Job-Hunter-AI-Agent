# utils/gcp_auth.py
"""
Google Cloud credentials loader.
Works both locally (credentials.json file)
and on Railway/cloud (GOOGLE_CREDENTIALS_JSON env variable).
"""

import os
import json
import tempfile
from loguru import logger


def get_google_credentials() -> str | None:
    """
    Returns path to a valid credentials JSON file.

    Priority:
    1. GOOGLE_CREDENTIALS_JSON env var  → used on Railway/cloud
    2. credentials.json file            → used locally
    """

    # ── Cloud (Railway) ──────────────────────────────────
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        try:
            parsed = json.loads(creds_json)
            tmp = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
            )
            json.dump(parsed, tmp)
            tmp.flush()
            tmp.close()
            logger.info("✅ Google credentials loaded from environment variable")
            return tmp.name
        except json.JSONDecodeError as e:
            logger.error(f"GOOGLE_CREDENTIALS_JSON is not valid JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to write credentials to temp file: {e}")

    # ── Local ─────────────────────────────────────────────
    creds_path = os.getenv("GOOGLE_SHEETS_CREDS_PATH", "credentials.json")
    if os.path.exists(creds_path):
        logger.info(f"✅ Google credentials loaded from file: {creds_path}")
        return creds_path

    logger.warning(
        "⚠️ No Google credentials found. "
        "Set GOOGLE_CREDENTIALS_JSON env var on Railway "
        "or place credentials.json in project root locally."
    )
    return None
