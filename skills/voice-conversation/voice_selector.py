#!/usr/bin/env python3
"""
Voice Selector - List and test available macOS voices
"""

import subprocess
import sys
import json

def list_voices():
    """List all available macOS voices"""
    try:
        # Use macOS `say` command to list voices
        cmd = ['say', '-v', '?']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            output = result.stdout
            voices = []

            # Parse voice list
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 1:
                        voice_name = parts[0]
                        # Get language and region if available
                        language = ' '.join(parts[1:]).strip('()') if len(parts) > 1 else 'Unknown'
                        voices.append({
                            "name": voice_name,
                            "language": language
                        })

            return voices
        else:
            return {"error": "Failed to list voices"}

    except Exception as e:
        return {"error": str(e)}

def test_voice(voice_name, text="Hello, this is a test of the voice system"):
    """
    Test a specific voice

    Args:
        voice_name: Voice identifier (e.g., 'Alex', 'Victoria', 'Samantha')
        text: Text to speak

    Returns:
        Success/error message
    """
    try:
        cmd = ['say', '-v', voice_name, text]
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0:
            return {
                "status": "success",
                "voice": voice_name,
                "message": f"Spoke with voice: {voice_name}"
            }
        else:
            return {
                "status": "error",
                "voice": voice_name,
                "error": result.stderr.decode() if result.stderr else "Unknown error"
            }

    except Exception as e:
        return {"status": "error", "error": str(e)}

def speak_with_voice(voice_name, text, output_file=None):
    """
    Generate speech with specific voice and save to file

    Args:
        voice_name: Voice identifier
        text: Text to speak
        output_file: Optional output file path

    Returns:
        Path to audio file or error
    """
    try:
        from pathlib import Path

        if output_file is None:
            import time
            output_file = Path.home() / ".agent-shared" / "voice" / "audio" / f"voice_{voice_name}_{int(time.time())}.aiff"
        else:
            output_file = Path(output_file)

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Use macOS say command to generate audio (aiff format works better)
        cmd = ['say', '-v', voice_name, '-o', str(output_file), text]
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and output_file.exists():
            return {
                "status": "success",
                "voice": voice_name,
                "output_file": str(output_file),
                "size_bytes": output_file.stat().st_size
            }
        else:
            error_msg = result.stderr.decode() if result.stderr else "Failed to generate speech"
            return {
                "status": "error",
                "error": error_msg[:200]
            }

    except Exception as e:
        return {"status": "error", "error": str(e)}

def get_voice_properties(voice_name):
    """
    Get detailed properties of a voice (if available)

    Args:
        voice_name: Voice identifier

    Returns:
        Voice properties dict
    """
    voices = list_voices()

    if isinstance(voices, dict) and "error" in voices:
        return voices

    for voice in voices:
        if voice["name"].lower() == voice_name.lower():
            return {
                "name": voice["name"],
                "language": voice["language"],
                "available": True
            }

    return {
        "name": voice_name,
        "available": False,
        "error": f"Voice '{voice_name}' not found"
    }

if __name__ == "__main__":
    import json

    if "--list" in sys.argv:
        voices = list_voices()
        if isinstance(voices, list):
            print(json.dumps(voices, indent=2))
        else:
            print(json.dumps(voices))

    elif "--test" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_selector.py --test <voice_name> [text]")
            sys.exit(1)

        voice = sys.argv[2]
        text = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "Hello, this is a test"

        result = test_voice(voice, text)
        print(json.dumps(result, indent=2))

    elif "--speak" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_selector.py --speak <voice_name> <text>")
            sys.exit(1)

        voice = sys.argv[2]
        text = " ".join(sys.argv[3:])

        result = speak_with_voice(voice, text)
        print(json.dumps(result, indent=2))

    elif "--play" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_selector.py --play <audio_file>")
            sys.exit(1)

        audio_file = sys.argv[2]
        result = play_audio(audio_file)
        print(json.dumps(result, indent=2))

    elif "--info" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_selector.py --info <voice_name>")
            sys.exit(1)

        voice = sys.argv[2]
        result = get_voice_properties(voice)
        print(json.dumps(result, indent=2))

    else:
        print("Voice Selector")
        print("Usage:")
        print("  python3 voice_selector.py --list")
        print("  python3 voice_selector.py --test <voice_name> [text]")
        print("  python3 voice_selector.py --speak <voice_name> <text>")
        print("  python3 voice_selector.py --info <voice_name>")
