#!/usr/bin/env python3
"""
Markdown Voice Respond - TTS only, reads responses from chat_loop.md and speaks them
"""

import re
import subprocess
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

# Load env
load_dotenv(Path.home() / ".env")
load_dotenv(Path.home() / "Documents/vibecoding/.env")

SHARED_DIR = Path.home() / ".agent-shared" / "voice"
AUDIO_DIR = SHARED_DIR / "audio"
CHAT_FILE = SHARED_DIR / "chat_loop.md"

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
CLAUDE_VOICE_ID = "ZoiZ8fuDWInAcwPXaVeq"  # Josh
USE_ELEVENLABS = ELEVENLABS_API_KEY is not None

def synthesize_speech(text):
    """Synthesize text to speech using ElevenLabs"""
    try:
        if not USE_ELEVENLABS:
            print("⚠️  ElevenLabs API key not found, using macOS say")
            output_file = AUDIO_DIR / f"response_{int(datetime.now().timestamp())}.aiff"
            cmd = ['say', '-v', 'Victoria', '-o', str(output_file), text]
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            if result.returncode == 0:
                return str(output_file)
            else:
                return None

        import requests

        output_file = AUDIO_DIR / f"response_{int(datetime.now().timestamp())}.mp3"

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{CLAUDE_VOICE_ID}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_flash_v2_5",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return str(output_file)
        else:
            print(f"ElevenLabs error: {response.text[:200]}")
            return None

    except Exception as e:
        print(f"Synthesis error: {e}")
        return None

def play_audio(audio_path):
    """Play audio file"""
    try:
        cmd = ['afplay', str(audio_path)]
        subprocess.run(cmd, capture_output=True, timeout=120)
        return True
    except Exception as e:
        print(f"Playback error: {e}")
        return False

def extract_response(chat_file):
    """Extract latest response from chat_loop.md"""
    try:
        with open(chat_file, 'r') as f:
            content = f.read()

        # Extract latest response (after last "Claude Response:")
        latest_match = re.search(r'### Turn \d+.*?\*\*Claude Response\*\*: (.+?)(?:###|\Z)', content, re.DOTALL)
        if latest_match:
            response_text = latest_match.group(1).strip()
            if response_text and response_text != "(awaiting input)":
                return response_text

        return None

    except Exception as e:
        print(f"Error reading chat file: {e}")
        return None

def main():
    print("\n🗣️  Markdown Voice Respond - Claude")
    print(f"Reads responses from {CHAT_FILE}")
    print("Synthesizes with Josh's voice (ElevenLabs)\n")

    if not CHAT_FILE.exists():
        print(f"❌ Chat file not found: {CHAT_FILE}")
        return

    print("👀 Looking for responses to speak...\n")

    response_text = extract_response(CHAT_FILE)

    if not response_text:
        print("❌ No response found or still awaiting input")
        print(f"👉 Add your response in {CHAT_FILE} under 'Claude Response:'")
        return

    print(f"📢 Found response:\n{response_text[:100]}...\n")

    audio_file = synthesize_speech(response_text)
    if not audio_file:
        print("❌ Failed to synthesize speech")
        return

    print(f"▶️  Playing response...\n")
    play_audio(audio_file)
    print("✅ Done")

if __name__ == "__main__":
    main()
