---
name: spotify-control
version: 0.1.0
description: Search and play music on Spotify via specific devices (Alexa, Echo, etc). Zero external dependencies — pure Python 3 stdlib.
triggers:
  - spotify
  - play music
  - alexa
  - play song
---

# Spotify Control Skill

Control Spotify playback from CLI. Search tracks, list devices, and play on any Spotify Connect device (Alexa, speakers, etc).

## Setup (one-time)

1. Go to https://developer.spotify.com/dashboard and create an app (select **Web API**)
2. Set Redirect URI to `http://127.0.0.1:3000`
3. Copy Client ID and Client Secret
4. Create `.env` in this skill folder (or set `SPOTIFY_ENV_FILE` env var to point elsewhere):

```
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3000
```

5. Run the auth flow once:

```bash
python3 spotify_auth.py
```

This starts a local server, opens a browser for Spotify approval, and saves the refresh token to `.spotify_token.json`. You only do this once — tokens auto-refresh after that.

## Usage

```bash
# List available Spotify Connect devices
python3 spotify_control.py devices

# Search for tracks
python3 spotify_control.py search "lo-fi beats"

# Play a song on a specific device (partial name match)
python3 spotify_control.py play "Bohemian Rhapsody" --device "Echo"

# Play with artist hint
python3 spotify_control.py play "APT by Bruno Mars" --device "Alexa"

# Play on whatever device is currently active
python3 spotify_control.py play "Chill Vibes"
```

## Features

- Smart track matching with scoring (title, artist, popularity)
- Supports `song by artist` and `song - artist` query formats
- Direct Spotify URI and URL support
- Partial device name matching with fuzzy selection
- Device index selection (use number from `devices` list)
- Auto token refresh (no re-auth needed)
- Zero external dependencies (pure stdlib `urllib`)

## Requirements

- Spotify Premium account (required for playback control)
- Python 3.10+
- Scopes: `user-read-playback-state user-modify-playback-state`

## Files

- `SKILL.md` — this file
- `spotify_auth.py` — one-time OAuth setup, saves refresh token
- `spotify_control.py` — main CLI: search, devices, play
- `.env` — your credentials (gitignored)
- `.spotify_token.json` — stored tokens (gitignored)
- `.gitignore` — excludes secrets from version control
