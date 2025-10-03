# collectors/facebook_collector.py
import os, re, math, hashlib, json, time
from datetime import datetime, timezone
import pandas as pd
from facebook_scraper import get_posts, set_user_agent
from utils.supabase_client import upsert_posts

PAGE_URLS = [u.strip() for u in os.environ.get("FB_PAGES", "https://www.facebook.com/Suwayda24,https://www.facebook.com/groups/zero0nine9").split(",")]
POSTS_LIMIT = int(os.environ.get("FB_LIMIT", "200"))
USER_AGENT = os.environ.get("FB_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def _identify(url: str):
    if not url: return "account", "", ""
    from urllib.parse import urlparse, parse_qs
    url = re.sub(r"^(https?://)(m\.|mbasic\.)?facebook\.com", r"\1www.facebook.com", url.strip())
    p = urlparse(url)
    path = (p.path or "").strip("/")
    if not path:
        return "account", "", url
    if path.startswith("groups/"):
        parts = path.split("/")
        ident = parts[1] if len(parts) > 1 else ""
        return "group", ident, f"https://www.facebook.com/groups/{ident}"
    if "profile.php" in (p.path or ""):
        q = parse_qs(p.query or "")
        pid = q.get("id", [""])[0]
        return "account", pid, f"https://www.facebook.com/profile.php?id={pid}"
    if "permalink.php" in (p.path or ""):
        q = parse_qs(p.query or "")
        pid = q.get("id", [""])[0]
        if pid: return "account", pid, f"https://www.facebook.com/profile.php?id={pid}"
    m = re.search(r"/people/[^/]+/(\d+)", p.path or "")
    if m:
        pid = m.group(1)
        return "account", pid, f"https://www.facebook.com/people/x/{pid}"
    ident = path.split("/")[0]
    return "account", ident, f"https://www.facebook.com/{ident}"

def _posts_from_url(url: str, limit: int):
    kind, ident, source_url = _identify(url)
    if not ident:
        print(f"Could not extract id: {url}")
        return []
    set_user_agent(USER_AGENT)
    per_page = 20
    pages = max(1, math.ceil((limit or 50)/per_page))
    options = {
        "progress": False, "allow_extra_requests": True, "posts_per_page": per_page, "comments": False,
        "request_kwargs": {"timeout": 30, "headers": {"Accept-Language": "ar,en-US;q=0.9,en;q=0.8"}},
    }
    cookies_json = os.environ.get("FB_COOKIES_JSON", "").strip()
    cookies = json.loads(cookies_json) if cookies_json else None

    results = []
    try:
        gen = get_posts(
            group=ident if kind=="group" else None,
            account=ident if kind=="account" else None,
            pages=pages,
            options=options,
            cookies=cookies,
        )
        for post in gen:
            iso_time = ""
            t = post.get("time")
            if t:
                try:
                    iso_time = t.astimezone(timezone.utc).isoformat()
                except Exception:
                    try:
                        iso_time = t.replace(tzinfo=timezone.utc).isoformat()
                    except Exception:
                        iso_time = ""
            results.append({
                "id": str(post.get("post_id") or ""),
                "content": post.get("text") or "",
                "created_at": iso_time,
                "author": {"name": ident, "username": ident},
                "url": post.get("post_url") or "",
                "metrics": {
                    "like_count": post.get("likes"),
                    "comment_count": post.get("comments"),
                    "share_count": post.get("shares"),
                },
                "owner_kind": kind,
                "source_url": source_url,
            })
            if len(results) >= (limit or 50): break
    except Exception as e:
        print(f"Failed on {url}: {e}")
        return []
    return results

def _to_rows(posts):
    rows = []
    for p in posts:
        content = p.get("content") or ""
        created = p.get("created_at")
        try:
            dt_iso = pd.to_datetime(created, errors="coerce", utc=True).isoformat()
        except Exception:
            dt_iso = ""
        source_url = p.get("source_url") or ""
        try:
            source_name = re.sub(r"https?://(www\.)?facebook\.com/","",source_url).strip("/").split("?")[0]
        except Exception:
            source_name = ""
        a = p.get("author") or {}
        author_name = (a.get("name") or a.get("username")) if isinstance(a, dict) else str(a or "")
        rows.append({
            "platform": "Facebook",
            "source_name": source_name,
            "source_url": source_url,
            "post_id": str(p.get("id") or ""),
            "post_url": p.get("url") or "",
            "author": author_name,
            "text": content,
            "language": "ar",
            "datetime_utc": dt_iso,
            "datetime_local": "",
            "admin_area": "",
            "locality": "",
            "geofenced_area": "",
            "tension_level": "",
            "media_urls": "",
            "shares": (p.get("metrics",{}) or {}).get("share_count") or "",
            "likes":  (p.get("metrics",{}) or {}).get("like_count") or "",
            "comments": (p.get("metrics",{}) or {}).get("comment_count") or "",
            "collected_at_utc": datetime.now(timezone.utc).isoformat(),
            "collector": "SHAJARA-Agent",
            "hash": hashlib.sha256((content or "").encode("utf-8")).hexdigest() if content else None,
            "notes": f"fb_owner={p.get('owner_kind') or ''}",
        })
    return rows

def main():
    all_posts = []
    remaining = POSTS_LIMIT
    for url in PAGE_URLS:
        if remaining <= 0: break
        chunk = min(remaining, 200)
        all_posts.extend(_posts_from_url(url, chunk))
        remaining = POSTS_LIMIT - len(all_posts)
    rows = _to_rows(all_posts)
    if rows:
        upsert_posts(rows)
        print(f"Inserted {len(rows)} Facebook rows into Supabase.")
    else:
        print("No Facebook rows collected.")

if __name__ == "__main__":
    main()
