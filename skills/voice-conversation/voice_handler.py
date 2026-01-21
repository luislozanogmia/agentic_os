#!/usr/bin/env python3
"""
Voice Conversation Skill - STT + TTS for real-time voice interaction
Optimized for M2 Mac using native frameworks + ElevenLabs
"""

import json
import subprocess
import os
from pathlib import Path
from datetime import datetime
import wave
import tempfile
from dotenv import load_dotenv

# Load environment variables from multiple locations (priority order)
# 1. ~/.env (home directory)
# 2. ~/Documents/vibecoding/.env (project directory)
load_dotenv(Path.home() / ".env")
load_dotenv(Path.home() / "Documents/vibecoding/.env")

# Shared directories
SHARED_DIR = Path.home() / ".agent-shared" / "voice"
SHARED_DIR.mkdir(parents=True, exist_ok=True)

AUDIO_DIR = SHARED_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

TRANSCRIPT_FILE = SHARED_DIR / "latest_transcript.json"
RESPONSE_FILE = SHARED_DIR / "latest_response.json"

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Voice assignments by agent:
# - Claude (male): Josh (ZoiZ8fuDWInAcwPXaVeq) - deep, warm, professional
# - Mia (female): Charlotte (XB0fDUnXU5powFXDhCwa) - cool, monotone, efficient
# - Gemini (neutral): EGPLqH9Wz2tNLu58EJVR - clear, articulate, analytical
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "ZoiZ8fuDWInAcwPXaVeq")  # Default: Josh (Claude's voice - deep, warm, professional)
USE_ELEVENLABS = ELEVENLABS_API_KEY is not None

def record_audio(duration=10, filename=None):
    """
    Record audio from microphone using macOS native tools

    Args:
        duration: Length in seconds
        filename: Optional filename (defaults to timestamp)

    Returns:
        Path to recorded audio file
    """
    try:
        if filename is None:
            filename = f"audio_{int(datetime.now().timestamp())}.wav"

        filepath = AUDIO_DIR / filename

        # Use SoX (brew install sox) for recording
        cmd = [
            'sox', '-d',
            '-r', '16000',  # 16kHz sample rate
            '-c', '1',      # Mono
            str(filepath),
            'trim', '0', str(duration)
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=duration + 5)

        if result.returncode == 0 and filepath.exists():
            return filepath
        else:
            print(f"Recording failed: {result.stderr.decode()}")
            return None

    except FileNotFoundError:
        print("Error: sox not installed")
        print("Install with: brew install sox")
        return None
    except Exception as e:
        print(f"Recording error: {e}")
        return None

def transcribe_audio(audio_path, model="base"):
    """
    Transcribe audio using Whisper

    Args:
        audio_path: Path to audio file
        model: Whisper model size (tiny, base, small, medium, large)

    Returns:
        Dict with transcription
    """
    try:
        # First check if audio file exists
        if not Path(audio_path).exists():
            return {"error": "Audio file not found"}

        # Use Whisper CLI
        cmd = [
            'whisper',
            str(audio_path),
            '--model', model,
            '--output_format', 'json',
            '--output_dir', str(SHARED_DIR),
            '--device', 'cpu'  # Use CPU to avoid CUDA issues
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=60)

        if result.returncode == 0:
            # Whisper outputs JSON with transcription
            json_file = Path(audio_path).stem + '.json'
            json_path = SHARED_DIR / json_file

            if json_path.exists():
                with open(json_path, 'r') as f:
                    data = json.load(f)

                transcript = {
                    "timestamp": datetime.now().isoformat(),
                    "audio_file": str(audio_path),
                    "text": data.get('text', ''),
                    "model": model,
                    "language": data.get('language', 'en')
                }

                # Save transcript
                with open(TRANSCRIPT_FILE, 'w') as f:
                    json.dump(transcript, f, indent=2)

                return transcript
            else:
                return {"error": "Transcription output not found"}
        else:
            error = result.stderr.decode() if result.stderr else "Unknown error"
            return {"error": f"Transcription failed: {error[:200]}"}

    except FileNotFoundError:
        return {"error": "Whisper not installed. Install with: pip install openai-whisper"}
    except Exception as e:
        return {"error": str(e)}

def synthesize_speech(text, output_file=None, voice=None, use_elevenlabs=None, play=True):
    """
    Convert text to speech using ElevenLabs (preferred) or macOS `say` (fallback)

    Args:
        text: Text to speak
        output_file: Optional output file path
        voice: Voice identifier (ElevenLabs voice_id or macOS voice name)
        use_elevenlabs: Force ElevenLabs (True) or macOS (False), None = auto-detect
        play: Automatically play audio after synthesis (default: True)

    Returns:
        Path to audio file or dict with result/error
    """
    try:
        if output_file is None:
            output_file = AUDIO_DIR / f"tts_{int(datetime.now().timestamp())}.mp3"
        else:
            output_file = Path(output_file)

        # Determine which backend to use
        use_eleven = use_elevenlabs if use_elevenlabs is not None else USE_ELEVENLABS

        if use_eleven:
            result = _synthesize_elevenlabs(text, output_file, voice)
        else:
            result = _synthesize_macos(text, output_file, voice)

        # Play audio automatically if requested and synthesis succeeded
        if play and isinstance(result, str):
            play_audio(result)

        return result

    except Exception as e:
        return {"error": str(e)}

def _synthesize_elevenlabs(text, output_file, voice_id=None):
    """
    Generate speech using ElevenLabs API

    Args:
        text: Text to speak
        output_file: Path to save audio
        voice_id: ElevenLabs voice ID (default: Bella)

    Returns:
        Path to audio file or error dict
    """
    try:
        if not ELEVENLABS_API_KEY:
            return _synthesize_macos(text, output_file, None)

        import requests

        voice_id = voice_id or ELEVENLABS_VOICE_ID

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": "eleven_flash_v2_5",  # Free tier model (v2.5 flash is cheaper)
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            with open(output_file, 'wb') as f:
                f.write(response.content)

            result = {
                "timestamp": datetime.now().isoformat(),
                "text": text,
                "output_file": str(output_file),
                "method": "ElevenLabs",
                "voice_id": voice_id,
                "size_bytes": output_file.stat().st_size
            }

            with open(RESPONSE_FILE, 'w') as f:
                json.dump(result, f, indent=2)

            return str(output_file)
        else:
            error_msg = response.text[:200]
            print(f"ElevenLabs API error: {error_msg}, falling back to macOS say")
            return _synthesize_macos(text, output_file, None)

    except ImportError:
        print("requests library not found, falling back to macOS say")
        return _synthesize_macos(text, output_file, None)
    except Exception as e:
        print(f"ElevenLabs error: {e}, falling back to macOS say")
        return _synthesize_macos(text, output_file, None)

def _synthesize_macos(text, output_file, voice=None):
    """
    Generate speech using macOS `say` command (fallback)

    Args:
        text: Text to speak
        output_file: Path to save audio
        voice: macOS voice name (default: Victoria)

    Returns:
        Path to audio file or error dict
    """
    try:
        voice = voice or "Victoria"

        # Change extension to .aiff for macOS
        if output_file.suffix != '.aiff':
            output_file = output_file.with_suffix('.aiff')

        cmd = ['say', '-v', voice, '-o', str(output_file), text]
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0:
            response = {
                "timestamp": datetime.now().isoformat(),
                "text": text,
                "output_file": str(output_file),
                "method": "macOS-say",
                "voice": voice,
                "size_bytes": output_file.stat().st_size
            }

            with open(RESPONSE_FILE, 'w') as f:
                json.dump(response, f, indent=2)

            return str(output_file)
        else:
            return {"error": f"TTS failed: {result.stderr.decode()[:200]}"}

    except Exception as e:
        return {"error": str(e)}

def play_audio(audio_path):
    """
    Play audio file on Mac

    Args:
        audio_path: Path to audio file

    Returns:
        Success/error message
    """
    try:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return {"error": "Audio file not found"}

        # Use afplay (Mac native audio player)
        cmd = ['afplay', str(audio_path)]
        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode == 0:
            return {"status": "Audio played successfully"}
        else:
            return {"error": result.stderr.decode()[:200]}

    except Exception as e:
        return {"error": str(e)}

def full_conversation_cycle(duration=5, whisper_model="base"):
    """
    Complete cycle: Record → Transcribe → (Ready for response) → Play response

    Args:
        duration: Recording length in seconds
        whisper_model: Whisper model size

    Returns:
        Dict with full conversation metadata
    """
    cycle = {
        "timestamp": datetime.now().isoformat(),
        "steps": {}
    }

    # Step 1: Record
    print("Recording...")
    audio_path = record_audio(duration=duration)
    cycle["steps"]["record"] = {
        "status": "success" if audio_path else "failed",
        "file": str(audio_path) if audio_path else None
    }

    if not audio_path:
        return cycle

    # Step 2: Transcribe
    print("Transcribing...")
    transcript = transcribe_audio(audio_path, model=whisper_model)
    cycle["steps"]["transcribe"] = transcript

    return cycle

def conversation_loop(agent_name="claude", duration=5, whisper_model="base"):
    """
    Real-time voice conversation loop: Record → Transcribe → Agent Response → Play → Repeat

    Args:
        agent_name: "claude", "mia", or "gemini"
        duration: Recording length per turn (seconds)
        whisper_model: Whisper model size

    Returns:
        Conversation history
    """
    # Agent voice mappings
    AGENTS = {
        "claude": {
            "voice_id": "ZoiZ8fuDWInAcwPXaVeq",
            "name": "Claude"
        },
        "mia": {
            "voice_id": "XB0fDUnXU5powFXDhCwa",
            "name": "Mia"
        },
        "gemini": {
            "voice_id": "EGPLqH9Wz2tNLu58EJVR",
            "name": "Gemini"
        }
    }

    if agent_name.lower() not in AGENTS:
        return {"error": f"Unknown agent. Choose from: {', '.join(AGENTS.keys())}"}

    agent = AGENTS[agent_name.lower()]
    conversation = {
        "agent": agent["name"],
        "started": datetime.now().isoformat(),
        "turns": []
    }

    print(f"\n🎤 Starting conversation with {agent['name']}")
    print(f"   Press Ctrl+C to end the conversation\n")

    turn = 0
    try:
        while True:
            turn += 1
            print(f"--- Turn {turn} ---")

            # Step 1: Record user voice
            print(f"⏱️  Recording for {duration} seconds... (speak now)")
            audio_path = record_audio(duration=duration)

            if not audio_path:
                print("❌ Recording failed, skipping turn")
                continue

            print(f"✅ Recorded")

            # Step 2: Transcribe user input
            print("📝 Transcribing...")
            transcript = transcribe_audio(audio_path, model=whisper_model)

            if "error" in transcript:
                print(f"❌ Transcription error: {transcript['error']}")
                continue

            user_message = transcript.get("text", "")
            print(f"📢 You: {user_message}")

            # Step 3: Prepare agent response (placeholder - integrate with actual agent)
            print(f"💭 {agent['name']} is thinking...")
            agent_response = f"I received your message: '{user_message}'. This is {agent['name']} speaking."

            # Step 4: Generate speech as agent
            print(f"🗣️  {agent['name']} responds (generating audio)...")
            audio_output = synthesize_speech(agent_response, voice=agent["voice_id"])

            if isinstance(audio_output, dict) and "error" in audio_output:
                print(f"❌ TTS Error: {audio_output['error']}")
                continue

            # Step 5: Play agent response
            print(f"▶️  Playing {agent['name']}'s response...\n")
            play_audio(audio_output)

            # Store turn in conversation history
            conversation["turns"].append({
                "turn": turn,
                "user_input": user_message,
                "agent_response": agent_response,
                "audio_file": audio_output
            })

    except KeyboardInterrupt:
        print(f"\n\n✅ Conversation ended. {turn} turns completed.")
        conversation["ended"] = datetime.now().isoformat()

    return conversation

def interactive_voice_session(agent_name="claude", duration=5, whisper_model="base"):
    """
    Interactive voice session: User speaks → Transcribe → Wait for human response → TTS

    This is designed for human-in-the-loop conversations where the user provides
    text responses that are then synthesized to speech.

    Args:
        agent_name: "claude", "mia", or "gemini"
        duration: Recording length per turn (seconds)
        whisper_model: Whisper model size

    Returns:
        Conversation history
    """
    AGENTS = {
        "claude": {
            "voice_id": "ZoiZ8fuDWInAcwPXaVeq",
            "name": "Claude"
        },
        "mia": {
            "voice_id": "XB0fDUnXU5powFXDhCwa",
            "name": "Mia"
        },
        "gemini": {
            "voice_id": "EGPLqH9Wz2tNLu58EJVR",
            "name": "Gemini"
        }
    }

    if agent_name.lower() not in AGENTS:
        return {"error": f"Unknown agent. Choose from: {', '.join(AGENTS.keys())}"}

    agent = AGENTS[agent_name.lower()]
    conversation = {
        "agent": agent["name"],
        "started": datetime.now().isoformat(),
        "turns": []
    }

    print(f"\n🎤 Interactive session with {agent['name']}")
    print(f"   Type 'quit' to end the session\n")

    turn = 0
    try:
        while True:
            turn += 1
            print(f"\n--- Turn {turn} ---")

            # Step 1: Record user voice
            print(f"⏱️  Recording for {duration} seconds... (speak now)")
            audio_path = record_audio(duration=duration)

            if not audio_path:
                print("❌ Recording failed, skipping turn")
                continue

            print(f"✅ Recorded")

            # Step 2: Transcribe user input
            print("📝 Transcribing...")
            transcript = transcribe_audio(audio_path, model=whisper_model)

            if "error" in transcript:
                print(f"❌ Transcription error: {transcript['error']}")
                continue

            user_message = transcript.get("text", "")
            print(f"\n📢 You said: {user_message}\n")

            # Step 3: Wait for agent response (human provides it)
            print(f"💬 {agent['name']}'s response (type below, then press Enter):")
            print("   (Type 'skip' to skip this turn, 'quit' to end session)\n")

            try:
                agent_response = input(f"{agent['name']}: ").strip()
            except EOFError:
                # Handle case where stdin is closed (running in background)
                print("(Waiting for response via stdin...)")
                agent_response = input(f"{agent['name']}: ").strip()

            if agent_response.lower() == 'quit':
                print(f"\n✅ Session ended by user.")
                break

            if agent_response.lower() == 'skip':
                print("⏭️  Skipped this turn")
                continue

            if not agent_response:
                print("⏭️  Empty response, skipping")
                continue

            # Step 4: Generate speech for agent response
            print(f"🗣️  Generating {agent['name']}'s voice...")
            audio_output = synthesize_speech(agent_response, voice=agent["voice_id"])

            if isinstance(audio_output, dict) and "error" in audio_output:
                print(f"❌ TTS Error: {audio_output['error']}")
                continue

            # Step 5: Play agent response
            print(f"▶️  Playing {agent['name']}'s response...\n")
            play_audio(audio_output)

            # Store turn in conversation history
            conversation["turns"].append({
                "turn": turn,
                "user_input": user_message,
                "agent_response": agent_response,
                "audio_file": audio_output
            })

    except KeyboardInterrupt:
        print(f"\n\n✅ Session ended. {turn} turns completed.")

    conversation["ended"] = datetime.now().isoformat()
    return conversation

if __name__ == "__main__":
    import sys

    if "--record" in sys.argv:
        duration = 10
        if "--duration" in sys.argv:
            idx = sys.argv.index("--duration")
            duration = int(sys.argv[idx + 1])

        print(f"Recording for {duration} seconds...")
        path = record_audio(duration=duration)
        if path:
            print(f"Recorded: {path}")
        else:
            print("Recording failed")

    elif "--transcribe" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_handler.py --transcribe <audio_file>")
            sys.exit(1)

        audio_file = sys.argv[2]
        model = "base"
        if "--model" in sys.argv:
            idx = sys.argv.index("--model")
            model = sys.argv[idx + 1]

        result = transcribe_audio(audio_file, model=model)
        print(json.dumps(result, indent=2))

    elif "--speak" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_handler.py --speak \"text to speak\" [--voice-id VOICE_ID]")
            sys.exit(1)

        text = sys.argv[2]
        voice_id = None
        if "--voice-id" in sys.argv:
            idx = sys.argv.index("--voice-id")
            voice_id = sys.argv[idx + 1]

        result = synthesize_speech(text, voice=voice_id)
        print(f"TTS output: {result}")

    elif "--play" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_handler.py --play <audio_file>")
            sys.exit(1)

        result = play_audio(sys.argv[2])
        print(json.dumps(result, indent=2))

    elif "--cycle" in sys.argv:
        duration = 5
        if "--duration" in sys.argv:
            idx = sys.argv.index("--duration")
            duration = int(sys.argv[idx + 1])

        result = full_conversation_cycle(duration=duration)
        print(json.dumps(result, indent=2))

    elif "--talk" in sys.argv:
        agent = "claude"
        duration = 5

        if len(sys.argv) > 2:
            agent = sys.argv[2]

        if "--duration" in sys.argv:
            idx = sys.argv.index("--duration")
            duration = int(sys.argv[idx + 1])

        conversation = conversation_loop(agent_name=agent, duration=duration)
        print(json.dumps(conversation, indent=2))

    elif "--interactive" in sys.argv:
        agent = "claude"
        duration = 5

        if len(sys.argv) > 2:
            agent = sys.argv[2]

        if "--duration" in sys.argv:
            idx = sys.argv.index("--duration")
            duration = int(sys.argv[idx + 1])

        conversation = interactive_voice_session(agent_name=agent, duration=duration)
        print(json.dumps(conversation, indent=2))

    else:
        print("Voice Handler - Talk to Claude, Mia, or Gemini")
        print("\nUsage:")
        print("  python3 voice_handler.py --record [--duration N]")
        print("  python3 voice_handler.py --transcribe <file> [--model base]")
        print("  python3 voice_handler.py --speak \"text\" [--voice-id VOICE_ID]")
        print("  python3 voice_handler.py --play <file>")
        print("  python3 voice_handler.py --cycle [--duration N]")
        print("  python3 voice_handler.py --talk <agent> [--duration N]")
        print("  python3 voice_handler.py --interactive <agent> [--duration N]  ← HUMAN-IN-THE-LOOP")
        print("\nExamples:")
        print("  python3 voice_handler.py --interactive claude          # Interactive with Claude")
        print("  python3 voice_handler.py --interactive mia --duration 3    # Interactive with Mia (3 sec recording)")
        print("  python3 voice_handler.py --interactive gemini          # Interactive with Gemini")
