#!/usr/bin/env python3
"""
Spotify OAuth 2.0 Authorization Code Flow — one-time setup.

Run this once to get a refresh token. After that, spotify_control.py
handles token refresh automatically.
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread

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

SCOPES = "user-read-playback-state user-modify-playback-state"
AUTH_URL = "https://accounts.spotify.com/authorize"
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
    """Load .env file into dict."""
    env = {}
    if not ENV_FILE.exists():
        sys.exit(f"No .env file found at {ENV_FILE}. Create it with SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI.")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


class CallbackHandler(BaseHTTPRequestHandler):
    """Captures the OAuth redirect callback."""
    auth_code = None

    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            CallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Auth complete! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code received.")

    def log_message(self, format, *args):
        pass  # suppress server logs


def main():
    env = load_env()
    client_id = env.get("SPOTIFY_CLIENT_ID")
    client_secret = env.get("SPOTIFY_CLIENT_SECRET")
    redirect_uri = env.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:3000")

    if not client_id or not client_secret:
        sys.exit("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in .env")

    # Build auth URL
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
    }
    auth_link = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    # Parse port from redirect URI
    parsed = urllib.parse.urlparse(redirect_uri)
    port = parsed.port or 3000

    # Start local server to catch callback
    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    thread = Thread(target=server.handle_request, daemon=True)
    thread.start()

    print(f"\n  Open this URL in your browser:\n\n  {auth_link}\n")
    print(f"  Waiting for callback on port {port}...")

    thread.join(timeout=120)
    server.server_close()

    if not CallbackHandler.auth_code:
        sys.exit("Timed out waiting for auth callback.")

    # Exchange code for tokens
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = _http_request("POST", TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": CallbackHandler.auth_code,
        "redirect_uri": redirect_uri,
    }, headers={
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    })

    if resp.status_code != 200:
        sys.exit(f"Token exchange failed: {resp.status_code} {resp.text}")

    tokens = resp.json()
    token_data = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "expires_in": tokens.get("expires_in", 3600),
    }
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    print(f"\n  Tokens saved to {TOKEN_FILE}")
    print("  Setup complete. You can now use spotify_control.py.")


if __name__ == "__main__":
    main()
