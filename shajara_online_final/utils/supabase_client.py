# utils/supabase_client.py (robust - handles 409 by per-row fallback)
import os
import requests
import datetime
from typing import List
from itertools import islice
import time

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_ANON_KEY"]
POSTS_ENDPOINT = f"{SUPABASE_URL}/rest/v1/posts"

HEADERS_BASE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def _normalize_rows(rows: List[dict]) -> List[dict]:
    # ensure datetimes are ISO strings, and convert empty hash -> None (so DB gets NULL)
    for r in rows:
        for k in ("datetime_utc", "collected_at_utc"):
            v = r.get(k)
            if hasattr(v, "isoformat"):
                r[k] = v.astimezone(datetime.timezone.utc).isoformat()
        # normalize hash: empty string -> None
        if "hash" in r:
            h = r.get("hash")
            if not h:
                r["hash"] = None
    return rows

def _chunked(iterable, size=100):
    it = iter(iterable)
    while True:
        chunk = list(islice(it, size))
        if not chunk:
            break
        yield chunk

def upsert_posts(rows: List[dict]):
    """
    Robust insert:
      - Normalize rows (datetime -> ISO, empty hash -> null)
      - Try batch insert (fast)
      - If batch raises 409 conflict, fall back to per-row insert and skip duplicates
    Returns dict with counts.
    """
    if not rows:
        return {"inserted": 0, "note": "no rows"}

    rows = _normalize_rows(rows)
    inserted_total = 0

    # Insert in manageable chunks
    for chunk in _chunked(rows, size=100):
        headers = HEADERS_BASE.copy()
        headers["Prefer"] = "return=minimal"
        try:
            resp = requests.post(POSTS_ENDPOINT, headers=headers, json=chunk, timeout=90)
            resp.raise_for_status()
            inserted_total += len(chunk)
            print(f"Batch inserted {len(chunk)} rows.")
        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            # if conflict -> try per-row to skip duplicates
            if status == 409:
                print("Batch conflict (409) — falling back to per-row insert for this chunk.")
                for row in chunk:
                    try:
                        # small delay to be polite to the server
                        time.sleep(0.05)
                        resp2 = requests.post(POSTS_ENDPOINT, headers=headers, json=[row], timeout=30)
                        resp2.raise_for_status()
                        inserted_total += 1
                    except requests.exceptions.HTTPError as e2:
                        st = getattr(e2.response, "status_code", None)
                        if st == 409:
                            # duplicate for this single row — skip it
                            print("  Skipped duplicate row (hash conflict).")
                            continue
                        else:
                            # other HTTP error: re-raise (we want to see details)
                            raise RuntimeError(f"HTTP error inserting a single row: {e2}") from e2
                    except Exception as ex:
                        raise RuntimeError(f"Unexpected error inserting a single row: {ex}") from ex
            else:
                # other HTTP error (not 409) — raise with context
                raise RuntimeError(f"Batch insert failed with status {status}: {e}") from e
        except Exception as ex:
            # network/timeout or other issues — stop and surface error
            raise RuntimeError(f"Batch insert unexpectedly failed: {ex}") from ex

    return {"status": 201, "count": inserted_total}
