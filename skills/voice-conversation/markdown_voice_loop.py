#!/usr/bin/env python3
"""
Markdown Voice Loop - STT only, writes to markdown for async review
Records user voice, transcribes, appends to chat_loop.md
"""

import json
import subprocess
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load env
load_dotenv(Path.home() / ".env")
load_dotenv(Path.home() / "Documents/vibecoding/.env")

SHARED_DIR = Path.home() / ".agent-shared" / "voice"
AUDIO_DIR = SHARED_DIR / "audio"
CHAT_FILE = SHARED_DIR / "chat_loop.md"

def record_audio(duration=10):
    """Record audio from mic"""
    try:
        filename = f"audio_{int(datetime.now().timestamp())}.wav"
        filepath = AUDIO_DIR / filename

        cmd = ['sox', '-d', '-r', '16000', '-c', '1', str(filepath), 'trim', '0', str(duration)]
        result = subprocess.run(cmd, capture_output=True, timeout=duration + 5)

        if result.returncode == 0 and filepath.exists():
            return filepath
        else:
            print(f"Recording failed: {result.stderr.decode()}")
            return None
    except Exception as e:
        print(f"Recording error: {e}")
        return None

def transcribe_audio(audio_path, model="base"):
    """Transcribe using Whisper"""
    try:
        if not Path(audio_path).exists():
            return {"error": "Audio file not found"}

        cmd = ['whisper', str(audio_path), '--model', model, '--output_format', 'json',
               '--output_dir', str(SHARED_DIR), '--device', 'cpu']
        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if result.returncode == 0:
            json_file = Path(audio_path).stem + '.json'
            json_path = SHARED_DIR / json_file
            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)
                return {"text": data.get('text', ''), "timestamp": datetime.now().isoformat()}
            else:
                return {"error": "Transcription output not found"}
        else:
            return {"error": f"Transcription failed: {result.stderr.decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}

def append_to_chat(user_text, turn_num):
    """Append user transcription to chat_loop.md"""
    try:
        with open(CHAT_FILE, 'a') as f:
            f.write(f"\n### Turn {turn_num}\n")
            f.write(f"**Timestamp**: {datetime.now().isoformat()}\n")
            f.write(f"**User Said**: {user_text}\n")
            f.write(f"**Claude Response**: (awaiting input)\n\n")
        return True
    except Exception as e:
        print(f"Error appending to chat: {e}")
        return False

def wait_for_key():
    """Wait for user to press any key (cross-platform)"""
    try:
        import sys
        import tty
        import termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    except Exception:
        # Fallback for non-Unix systems
        input()

def main():
    print("\n🎤 Markdown Voice Loop - Claude")
    print("Records your voice → Transcribes → Writes to chat_loop.md")
    print("Press Ctrl+C to stop\n")

    turn = 0
    try:
        while True:
            turn += 1
            print(f"\n--- Turn {turn} ---")
            print(f"⏱️  Recording for 5 seconds... (speak now)")

            audio_path = record_audio(duration=5)
            if not audio_path:
                print("❌ Recording failed, skipping turn")
                continue

            print(f"✅ Recorded")
            print("📝 Transcribing...")

            result = transcribe_audio(audio_path, model="base")

            if "error" in result:
                print(f"❌ Transcription error: {result['error']}")
                continue

            user_text = result.get("text", "")
            print(f"\n📢 You said: {user_text}\n")

            # Append to chat_loop.md
            if append_to_chat(user_text, turn):
                print(f"✅ Appended to chat_loop.md")
                print(f"👉 Review and respond in: {CHAT_FILE}")
                print("\n⏳ Waiting for Claude to respond...")
                print("Press any key to record another audio message")
                wait_for_key()
            else:
                print("❌ Failed to append to chat_loop.md")

    except KeyboardInterrupt:
        print(f"\n\n✅ Session ended. {turn} turns recorded.")

if __name__ == "__main__":
    main()
