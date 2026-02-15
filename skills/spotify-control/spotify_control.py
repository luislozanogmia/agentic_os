#!/usr/bin/env python3
"""
Spotify Control — search tracks, list devices, play on a specific device.

Usage:
    python3 spotify_control.py devices
    python3 spotify_control.py search "query"
    python3 spotify_control.py play "query" --device "Echo"
"""

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

class _SimpleResponse:
    def __init__(self, status_code, text, headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def json(self):
        if not self.text:
            return {}
        return json.loads(self.text)

SKILL_DIR = Path(__file__).parent
# Point this to the .env file containing SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
# Default: .env in the same folder as this script. Override via SPOTIFY_ENV_FILE env var.
ENV_FILE = Path(os.environ.get("SPOTIFY_ENV_FILE", SKILL_DIR / ".env"))
TOKEN_FILE = SKILL_DIR / ".spotify_token.json"
API_BASE = "https://api.spotify.com/v1"
TOKEN_URL = "https://accounts.spotify.com/api/token"


def _http_request(method, url, *, headers=None, params=None, data=None, json_body=None, timeout=20):
    headers = dict(headers or {})

    if params:
        parsed = urllib.parse.urlparse(url)
        existing = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        for k, v in params.items():
            if v is None:
                continue
            existing[k] = v
        url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(existing)))

    body = None
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    elif data is not None:
        if isinstance(data, dict):
            body = urllib.parse.urlencode(data).encode("utf-8")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = data
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8") if raw else ""
            return _SimpleResponse(resp.getcode(), text, dict(resp.headers))
    except urllib.error.HTTPError as e:
        raw = e.read()
        text = raw.decode("utf-8") if raw else ""
        return _SimpleResponse(e.code, text, dict(e.headers))
    except urllib.error.URLError as e:
        return _SimpleResponse(0, str(e), {})


def load_env():
    env = {}
    if not ENV_FILE.exists():
        sys.exit(f"No .env at {ENV_FILE}")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def load_tokens():
    if not TOKEN_FILE.exists():
        sys.exit("No tokens found. Run spotify_auth.py first.")
    return json.loads(TOKEN_FILE.read_text())


def save_tokens(data):
    TOKEN_FILE.write_text(json.dumps(data, indent=2))


def refresh_access_token(env, tokens):
    """Refresh the access token using the stored refresh token."""
    client_id = env["SPOTIFY_CLIENT_ID"]
    client_secret = env["SPOTIFY_CLIENT_SECRET"]
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    resp = _http_request("POST", TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
    }, headers={
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    })

    if resp.status_code != 200:
        sys.exit(f"Token refresh failed: {resp.status_code} {resp.text}")

    new = resp.json()
    tokens["access_token"] = new["access_token"]
    if "refresh_token" in new:
        tokens["refresh_token"] = new["refresh_token"]
    tokens["refreshed_at"] = int(time.time())
    save_tokens(tokens)
    return tokens


def get_headers(env):
    """Get auth headers, refreshing token if needed."""
    tokens = load_tokens()
    refreshed_at = tokens.get("refreshed_at", 0)
    expires_in = tokens.get("expires_in", 3600)
    if time.time() - refreshed_at > expires_in - 300:
        tokens = refresh_access_token(env, tokens)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _norm_text(value: str) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str) -> set[str]:
    normalized = _norm_text(value)
    return set(normalized.split()) if normalized else set()


def _extract_track_uri(query: str) -> str | None:
    raw = (query or "").strip()
    if not raw:
        return None

    if raw.startswith("spotify:track:"):
        return raw

    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(raw)
        except Exception:
            return None
        if "open.spotify.com" not in (parsed.netloc or ""):
            return None
        parts = [p for p in (parsed.path or "").split("/") if p]
        if len(parts) >= 2 and parts[0] == "track":
            track_id = parts[1].split("?", 1)[0].strip()
            if track_id:
                return f"spotify:track:{track_id}"
    return None


def _parse_song_artist(query: str) -> tuple[str, str | None, str | None]:
    raw = (query or "").strip()
    if not raw:
        return "", None, None

    lowered = raw.lower()
    idx = lowered.rfind(" by ")
    if idx != -1:
        song = raw[:idx].strip()
        artist = raw[idx + 4 :].strip()
        if song and artist:
            return raw, song, artist

    if " - " in raw:
        song, _, artist = raw.partition(" - ")
        song = song.strip()
        artist = artist.strip()
        if song and artist:
            return raw, song, artist

    return raw, None, None


def _search_tracks(env, query: str, limit: int = 10) -> list[dict]:
    headers = get_headers(env)
    resp = _http_request(
        "GET",
        f"{API_BASE}/search",
        headers=headers,
        params={"q": query, "type": "track", "limit": limit},
    )
    if resp.status_code != 200:
        sys.exit(f"Search failed: {resp.status_code} {resp.text}")
    return resp.json().get("tracks", {}).get("items", []) or []


def _track_score(track: dict, *, query: str, song: str | None = None, artist: str | None = None) -> int:
    title = track.get("name") or ""
    artist_names = ", ".join(a.get("name", "") for a in (track.get("artists") or []) if isinstance(a, dict))

    q_norm = _norm_text(song or query)
    title_norm = _norm_text(title)
    artists_norm = _norm_text(artist_names)

    score = 0
    if q_norm and title_norm == q_norm:
        score += 1000
    if q_norm and title_norm.startswith(q_norm):
        score += 650
    if q_norm and q_norm in title_norm:
        score += 450
    if q_norm and title_norm and title_norm in q_norm:
        score += 250

    q_tokens = _tokens(song or query)
    title_tokens = _tokens(title)
    score += 45 * len(q_tokens & title_tokens)

    if artist:
        a_norm = _norm_text(artist)
        if a_norm and a_norm in artists_norm:
            score += 400
        score += 20 * len(_tokens(artist) & _tokens(artist_names))

    score += 10 * len(_tokens(query) & _tokens(artist_names))

    popularity = track.get("popularity")
    if isinstance(popularity, int):
        score += popularity
    return score


def _pick_best_track(tracks: list[dict], *, query: str, song: str | None = None, artist: str | None = None) -> dict:
    best = None
    best_score = -1
    for t in tracks:
        if not isinstance(t, dict):
            continue
        score = _track_score(t, query=query, song=song, artist=artist)
        if score > best_score:
            best = t
            best_score = score
    if best is None:
        raise SystemExit(f"No tracks found for '{query}'")
    return best


def _select_device(devices: list[dict], device_name: str) -> dict:
    raw = (device_name or "").strip()
    if not raw:
        raise SystemExit("Device name was empty.")

    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(devices):
            return devices[idx - 1]
        raise SystemExit(f"Device index {idx} is out of range. Run: spotify_control.py devices")

    lowered = raw.lower()
    exact = [d for d in devices if (d.get("name") or "").lower() == lowered]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        active = [d for d in exact if d.get("is_active")]
        if len(active) == 1:
            return active[0]
        options = ", ".join(d.get("name", "?") for d in exact)
        raise SystemExit(f"Device '{device_name}' matches multiple devices: {options}. Use a more specific name or a numeric index.")

    partial = [d for d in devices if lowered in (d.get("name") or "").lower()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        active = [d for d in partial if d.get("is_active")]
        if len(active) == 1:
            return active[0]
        options = ", ".join(d.get("name", "?") for d in partial)
        raise SystemExit(f"Device '{device_name}' matches multiple devices: {options}. Use a more specific name or a numeric index.")

    available = ", ".join(d.get("name", "?") for d in devices) or "none"
    raise SystemExit(f"Device '{device_name}' not found. Available: {available}")


def cmd_devices(env):
    """List available Spotify Connect devices."""
    headers = get_headers(env)
    resp = _http_request("GET", f"{API_BASE}/me/player/devices", headers=headers)
    if resp.status_code != 200:
        sys.exit(f"Failed: {resp.status_code} {resp.text}")

    devices = resp.json().get("devices", [])
    if not devices:
        print("No active devices found. Open Spotify on a device first.")
        return

    for idx, d in enumerate(devices, start=1):
        active = " (active)" if d.get("is_active") else ""
        print(f"{idx}. {d['name']} — {d['type']} — {d['id']}{active}")


def cmd_search(env, query, limit=5):
    """Search for tracks."""
    tracks = _search_tracks(env, query, limit=limit)
    if not tracks:
        print(f"No tracks found for '{query}'")
        return []

    for i, t in enumerate(tracks):
        artists = ", ".join(a["name"] for a in t["artists"])
        print(f"{i+1}. {t['name']} — {artists} [{t['uri']}]")
    return tracks


def cmd_play(env, query, device_name=None):
    """Search for a track and play it on a device."""
    headers = get_headers(env)

    direct_uri = _extract_track_uri(query)
    raw_query, song, artist = _parse_song_artist(query)

    track = None
    if direct_uri:
        track_id = direct_uri.split(":")[-1]
        info = _http_request("GET", f"{API_BASE}/tracks/{track_id}", headers=headers)
        if info.status_code == 200:
            track = info.json()
        else:
            track = {"uri": direct_uri, "name": raw_query, "artists": []}
    else:
        qualified = raw_query
        if song and artist:
            qualified = f'track:"{song}" artist:"{artist}"'
        tracks = _search_tracks(env, qualified, limit=10)
        if not tracks and qualified != raw_query:
            tracks = _search_tracks(env, raw_query, limit=10)
        if not tracks:
            sys.exit(f"No tracks found for '{raw_query}'")
        track = _pick_best_track(tracks, query=raw_query, song=song, artist=artist)

    artists = ", ".join(a.get("name", "") for a in (track.get("artists") or []) if isinstance(a, dict))
    display = f"{track.get('name') or raw_query}" + (f" — {artists}" if artists else "")
    print(f"  Playing: {display}")

    # Find device
    device_id = None
    if device_name:
        resp = _http_request("GET", f"{API_BASE}/me/player/devices", headers=headers)
        if resp.status_code != 200:
            sys.exit(f"Failed to fetch devices: {resp.status_code} {resp.text}")
        devices = resp.json().get("devices", []) or []
        if not devices:
            sys.exit("No active devices found. Open Spotify on a device first.")

        chosen = _select_device(devices, device_name)
        device_id = chosen.get("id")
        print(f"  Device: {chosen.get('name', device_name)}")

    # Transfer playback to device first (activates it), then play
    if device_id:
        _http_request("PUT", f"{API_BASE}/me/player", headers=headers, json_body={
            "device_ids": [device_id],
            "play": False,
        })
        time.sleep(1)

    play_url = f"{API_BASE}/me/player/play"
    if device_id:
        play_url += f"?device_id={device_id}"

    resp = _http_request("PUT", play_url, headers=headers, json_body={
        "uris": [track["uri"]],
    })

    if resp.status_code in (200, 204):
        print("  Started playback.")
    elif resp.status_code == 404:
        sys.exit("No active device. Open Spotify somewhere first.")
    else:
        sys.exit(f"Play failed: {resp.status_code} {resp.text}")


def main():
    parser = argparse.ArgumentParser(description="Spotify Control")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("devices", help="List Spotify Connect devices")

    sp_search = sub.add_parser("search", help="Search for tracks")
    sp_search.add_argument("query", help="Search query")

    sp_play = sub.add_parser("play", help="Search and play a track")
    sp_play.add_argument("query", help="Song/artist to play")
    sp_play.add_argument("--device", "-d", help="Device name or numeric index from devices list")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    env = load_env()

    if args.command == "devices":
        cmd_devices(env)
    elif args.command == "search":
        cmd_search(env, args.query)
    elif args.command == "play":
        cmd_play(env, args.query, args.device)


if __name__ == "__main__":
    main()
