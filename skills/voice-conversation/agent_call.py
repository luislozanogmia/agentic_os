#!/usr/bin/env python3
"""
Agent Voice Call System - Call Claude, Mia, or Gemini by voice
Real-time voice interaction with intelligent agent routing
"""

import sys
import json
import subprocess
from pathlib import Path
from voice_handler import synthesize_speech, record_audio, transcribe_audio, play_audio

# Agent voice mappings
AGENTS = {
    "claude": {
        "voice_id": "ZoiZ8fuDWInAcwPXaVeq",
        "name": "Claude",
        "description": "Deep, warm, professional reasoning",
        "skill": "Complex reasoning, architecture, long-form explanations"
    },
    "mia": {
        "voice_id": "XB0fDUnXU5powFXDhCwa",
        "name": "Mia",
        "description": "Cool, monotone, efficient validator",
        "skill": "Validation, refusal, structural decisions"
    },
    "gemini": {
        "voice_id": "EGPLqH9Wz2tNLu58EJVR",
        "name": "Gemini",
        "description": "Clear, articulate, analytical reasoning",
        "skill": "Fast reasoning, multimodal tasks, information synthesis"
    }
}

def speak_as_agent(agent_name, text):
    """
    Synthesize speech as a specific agent

    Args:
        agent_name: "claude", "mia", or "gemini"
        text: Text to speak

    Returns:
        Path to audio file
    """
    if agent_name.lower() not in AGENTS:
        return {"error": f"Unknown agent. Choose from: {', '.join(AGENTS.keys())}"}

    agent = AGENTS[agent_name.lower()]
    result = synthesize_speech(text, voice=agent["voice_id"])

    if isinstance(result, str):
        return {
            "status": "success",
            "agent": agent["name"],
            "audio_file": result
        }
    else:
        return result

def call_agent(agent_name, duration=5):
    """
    Full voice call cycle: Record user → Send to agent → Agent responds → Play response

    Args:
        agent_name: "claude", "mia", or "gemini"
        duration: Recording duration in seconds

    Returns:
        Call metadata dict
    """
    if agent_name.lower() not in AGENTS:
        print(f"❌ Unknown agent. Choose from: {', '.join(AGENTS.keys())}")
        return None

    agent = AGENTS[agent_name.lower()]

    print(f"\n🎤 Calling {agent['name']}...")
    print(f"   Tone: {agent['description']}")
    print(f"   Skills: {agent['skill']}")
    print(f"\n⏱️  Recording for {duration} seconds... (speak now)")

    # Step 1: Record user voice
    audio_path = record_audio(duration=duration)
    if not audio_path:
        print("❌ Recording failed")
        return None

    print(f"✅ Recorded: {audio_path}")

    # Step 2: Transcribe
    print("📝 Transcribing...")
    transcript = transcribe_audio(audio_path, model="base")

    if "error" in transcript:
        print(f"❌ Transcription error: {transcript['error']}")
        return None

    user_message = transcript.get("text", "")
    print(f"📢 You said: {user_message}")

    # Step 3: Simulate agent response (placeholder - in real use, would call actual agent API)
    print(f"\n💭 {agent['name']} is thinking...")
    agent_response = f"Thank you for reaching out. I received your message: '{user_message}'. This is {agent['name']} speaking."

    # Step 4: Agent responds via voice
    print(f"🗣️  {agent['name']} responds (generating audio)...")
    audio_output = speak_as_agent(agent_name, agent_response)

    if isinstance(audio_output, dict) and "error" in audio_output:
        print(f"❌ TTS Error: {audio_output['error']}")
        return None

    # Step 5: Play agent response
    print(f"▶️  Playing {agent['name']}'s response...\n")
    play_result = play_audio(audio_output["audio_file"])

    if isinstance(play_result, dict) and "status" in play_result:
        print(f"✅ {play_result['status']}")

    return {
        "agent": agent["name"],
        "user_input": user_message,
        "agent_response": agent_response,
        "audio_file": audio_output.get("audio_file") if isinstance(audio_output, dict) else audio_output
    }

def list_agents():
    """Show available agents"""
    print("\n🤖 Available Agents:\n")
    for key, agent in AGENTS.items():
        print(f"  {key.upper():10} - {agent['name']:15} {agent['description']}")
        print(f"             Skills: {agent['skill']}\n")

def main():
    if len(sys.argv) < 2:
        print("Agent Voice Call System")
        print("\nUsage:")
        print("  python3 agent_call.py <agent> [duration]")
        print("  python3 agent_call.py speak <agent> \"text\"")
        print("  python3 agent_call.py list")
        print("\nExamples:")
        print("  python3 agent_call.py claude 5        # Call Claude for 5 seconds")
        print("  python3 agent_call.py mia             # Call Mia (default 5 sec)")
        print("  python3 agent_call.py speak gemini \"Hello Gemini\"")
        print("  python3 agent_call.py list            # Show all agents")
        return

    command = sys.argv[1].lower()

    if command == "list":
        list_agents()

    elif command == "speak":
        if len(sys.argv) < 4:
            print("Usage: python3 agent_call.py speak <agent> \"text\"")
            sys.exit(1)

        agent_name = sys.argv[2]
        text = " ".join(sys.argv[3:])

        result = speak_as_agent(agent_name, text)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ {result['agent']} speaking...")
            print(f"   Audio: {result['audio_file']}")

    else:
        # Call agent with optional duration
        agent_name = command
        duration = 5

        if len(sys.argv) > 2:
            try:
                duration = int(sys.argv[2])
            except ValueError:
                print(f"Invalid duration: {sys.argv[2]}")
                sys.exit(1)

        call_result = call_agent(agent_name, duration=duration)

        if call_result:
            print(f"\n✅ Call Summary:")
            print(f"   Agent: {call_result['agent']}")
            print(f"   You said: {call_result['user_input']}")
            print(f"   Response: {call_result['agent_response'][:80]}...")

if __name__ == "__main__":
    main()
