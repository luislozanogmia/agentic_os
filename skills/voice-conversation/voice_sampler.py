#!/usr/bin/env python3
"""
Voice Sampler - Generate audio samples of different voices
Organized by: Professional (Male/Female), Fun, Multilingual
"""

import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime

SAMPLE_TEXT = "Hello, I'm your AI assistant. How can I help you today?"

# Voice collections
VOICES = {
    "professional_male": [
        "Daniel",      # Professional, clear male
        "Thomas",      # Deep, professional
        "Ralph",       # Warm, professional
        "Fred",        # Natural male voice
        "Albert",      # Clear English male
    ],
    "professional_female": [
        "Victoria",    # Professional, clear female
        "Samantha",    # Friendly, clear female
        "Moira",       # Natural female (Irish)
        "Karen",       # Clear female (Australian)
        "Tessa",       # Pleasant female (South African)
    ],
    "fun_voices": [
        "Wobble",      # Wobbly, funny
        "Bubbles",     # Bubbly, playful
        "Jester",      # Playful character
        "Rocko",       # Rocky character
        "Superstar",   # Confident/arrogant
        "Whisper",     # Whispered
        "Good",        # "Good" sounds
        "Bahh",        # Sheep sounds
        "Boing",       # Boing effects
        "Bells",       # Bell sounds
    ],
    "multilingual": [
        ("Jacques", "French: Bonjour! Je suis Claude."),
        ("Amélie", "French Canadian: Bonjour, comment allez-vous?"),
        ("Kyoto", "Japanese: こんにちは"),
        ("Tingting", "Chinese: 你好，我是你的AI助手"),
        ("Majed", "Arabic: مرحبا، أنا مساعدك الذكي"),
    ]
}

def generate_samples(category="all"):
    """Generate voice samples"""
    output_dir = Path.home() / ".agent-shared" / "voice" / "samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = []

    print(f"\n🎤 Generating voice samples to: {output_dir}\n")

    if category in ["all", "professional_male"]:
        print("👨 Professional Male Voices:")
        for voice in VOICES["professional_male"]:
            filepath = generate_sample(voice, SAMPLE_TEXT, output_dir)
            if filepath:
                print(f"  ✓ {voice:15} → {filepath.name}")
                samples.append({"category": "professional_male", "voice": voice, "file": str(filepath)})

    if category in ["all", "professional_female"]:
        print("\n👩 Professional Female Voices:")
        for voice in VOICES["professional_female"]:
            filepath = generate_sample(voice, SAMPLE_TEXT, output_dir)
            if filepath:
                print(f"  ✓ {voice:15} → {filepath.name}")
                samples.append({"category": "professional_female", "voice": voice, "file": str(filepath)})

    if category in ["all", "fun"]:
        print("\n🎉 Fun/Character Voices:")
        for voice in VOICES["fun_voices"]:
            filepath = generate_sample(voice, SAMPLE_TEXT, output_dir)
            if filepath:
                print(f"  ✓ {voice:15} → {filepath.name}")
                samples.append({"category": "fun", "voice": voice, "file": str(filepath)})

    if category in ["all", "multilingual"]:
        print("\n🌍 Multilingual Voices:")
        for voice, text in VOICES["multilingual"]:
            filepath = generate_sample(voice, text, output_dir)
            if filepath:
                print(f"  ✓ {voice:15} → {filepath.name}")
                samples.append({"category": "multilingual", "voice": voice, "file": str(filepath)})

    # Save manifest
    manifest_file = output_dir / "manifest.json"
    with open(manifest_file, 'w') as f:
        json.dump(samples, f, indent=2)

    print(f"\n✅ Manifest saved: {manifest_file}")
    return samples

def generate_sample(voice, text, output_dir):
    """Generate a single voice sample"""
    try:
        timestamp = int(datetime.now().timestamp())
        filename = f"{voice}_{timestamp}.aiff"
        filepath = output_dir / filename

        cmd = ['say', '-v', voice, '-o', str(filepath), text]
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0 and filepath.exists():
            return filepath
        else:
            return None

    except Exception as e:
        print(f"Error generating {voice}: {e}")
        return None

def play_sample(voice):
    """Play a voice sample"""
    output_dir = Path.home() / ".agent-shared" / "voice" / "samples"

    # Find the latest sample for this voice
    samples = sorted(output_dir.glob(f"{voice}_*.aiff"), reverse=True)

    if not samples:
        print(f"No sample found for voice: {voice}")
        return False

    filepath = samples[0]
    cmd = ['afplay', str(filepath)]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        print(f"Playing: {voice}")
        return True
    else:
        print(f"Failed to play: {voice}")
        return False

def list_samples():
    """List all generated samples"""
    output_dir = Path.home() / ".agent-shared" / "voice" / "samples"
    manifest_file = output_dir / "manifest.json"

    if not manifest_file.exists():
        print("No samples generated yet. Run: python3 voice_sampler.py --generate")
        return

    with open(manifest_file, 'r') as f:
        samples = json.load(f)

    print("\n📋 Available Voice Samples:\n")

    categories = {}
    for sample in samples:
        cat = sample["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(sample["voice"])

    for category, voices in categories.items():
        print(f"{category.replace('_', ' ').title()}:")
        for voice in voices:
            print(f"  • {voice}")
        print()

def show_recommendations():
    """Show recommended voice selections"""
    print("\n" + "="*60)
    print("🎯 RECOMMENDED VOICE PAIRINGS FOR YOUR TEAM")
    print("="*60)

    print("\n👨 CLAUDE (You suggested 'he'):")
    print("  Recommended: Daniel or Thomas")
    print("  Why: Professional, authoritative, clear")
    print("  Command: python3 voice_sampler.py --test Daniel")

    print("\n👩 MIA (She):")
    print("  Recommended: Victoria or Moira")
    print("  Why: Professional, friendly, natural")
    print("  Command: python3 voice_sampler.py --test Victoria")

    print("\n🤖 GEMINI (Neutral):")
    print("  Recommended: Karen or Samantha")
    print("  Why: Clear, articulate, distinctive")
    print("  Command: python3 voice_sampler.py --test Karen")

    print("\n" + "="*60)

if __name__ == "__main__":
    if "--generate" in sys.argv:
        category = "all"
        if "--category" in sys.argv:
            idx = sys.argv.index("--category")
            category = sys.argv[idx + 1]

        generate_samples(category)

    elif "--list" in sys.argv:
        list_samples()

    elif "--test" in sys.argv:
        if len(sys.argv) < 3:
            print("Usage: python3 voice_sampler.py --test <voice_name>")
            sys.exit(1)

        voice = sys.argv[2]
        play_sample(voice)

    elif "--recommendations" in sys.argv:
        show_recommendations()

    elif "--quick" in sys.argv:
        print("🚀 Quick voice test (professional voices only):\n")
        output_dir = Path.home() / ".agent-shared" / "voice" / "samples"
        output_dir.mkdir(parents=True, exist_ok=True)

        print("👨 Male voices:")
        for voice in ["Daniel", "Thomas"]:
            filepath = generate_sample(voice, "Hello, I'm Claude", output_dir)
            if filepath:
                print(f"  Generated: {voice}")

        print("\n👩 Female voices:")
        for voice in ["Victoria", "Moira"]:
            filepath = generate_sample(voice, "Hello, I'm Mia", output_dir)
            if filepath:
                print(f"  Generated: {voice}")

        print("\n✅ Quick samples generated!")

    else:
        print("Voice Sampler - Test different voice personalities")
        print("\nUsage:")
        print("  python3 voice_sampler.py --generate              # Generate all samples")
        print("  python3 voice_sampler.py --generate --category professional_male")
        print("  python3 voice_sampler.py --list                 # Show generated samples")
        print("  python3 voice_sampler.py --test <voice_name>    # Play a sample")
        print("  python3 voice_sampler.py --recommendations      # See pairing suggestions")
        print("  python3 voice_sampler.py --quick                # Quick male/female test")
        print("\nVoice Categories:")
        print("  • professional_male")
        print("  • professional_female")
        print("  • fun")
        print("  • multilingual")
