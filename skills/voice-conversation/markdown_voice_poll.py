#!/usr/bin/env python3
"""
Markdown Voice Poll - Monitor and respond to chat_loop.md every 10 seconds
Reads Claude responses from markdown, synthesizes to speech, plays audio
"""

import re
import subprocess
import os
import time
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

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

def extract_latest_response(chat_file):
    """Extract the latest Claude response that hasn't been played yet"""
    try:
        with open(chat_file, 'r') as f:
            content = f.read()

        # Find ALL Claude responses
        matches = list(re.finditer(r'### Turn \d+.*?\*\*Claude Response\*\*: (.+?)(?:###|\Z)', content, re.DOTALL))

        if not matches:
            return None, None

        # Get the latest match
        latest_match = matches[-1]
        response_text = latest_match.group(1).strip()

        if response_text and response_text != "(awaiting input)":
            return response_text, latest_match.start()

        return None, None

    except Exception as e:
        print(f"Error reading chat file: {e}")
        return None, None

def main():
    print("\n🎙️ Markdown Voice Poll - Claude")
    print(f"Monitoring {CHAT_FILE} every 10 seconds")
    print("Press Ctrl+C to stop\n")

    last_response_pos = 0

    try:
        while True:
            print(f"\n=== {datetime.now().strftime('%H:%M:%S')} CHECKING FOR RESPONSES ===")

            response_text, response_pos = extract_latest_response(CHAT_FILE)

            if response_text:
                # Only play if this is a new response (position changed)
                if response_pos != last_response_pos:
                    last_response_pos = response_pos
                    print(f"📢 Found new response:")
                    print(f"   {response_text[:100]}...")

                    audio_file = synthesize_speech(response_text)
                    if audio_file:
                        print(f"▶️  Playing response...\n")
                        play_audio(audio_file)
                        print("✅ Done playing")
                    else:
                        print("❌ Failed to synthesize speech")
                else:
                    print("(No new responses)")
            else:
                print("(No responses yet or still awaiting input)")

            print(f"⏳ Sleeping 10 seconds...")
            time.sleep(10)

    except KeyboardInterrupt:
        print(f"\n\n✅ Poll stopped.")

if __name__ == "__main__":
    main()
