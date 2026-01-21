# Available macOS Voices

Your M2 Mac comes with **160+ voices** in multiple languages. Here's how to use them:

## Quick Voice Test

```bash
# List all voices
python3 ~/.claude/skills/voice-conversation/voice_selector.py --list

# Test a voice
python3 ~/.claude/skills/voice-conversation/voice_selector.py --test "Victoria" "Hello, this is Victoria"

# Save voice to file
python3 ~/.claude/skills/voice-conversation/voice_selector.py --speak "Albert" "I am Albert" > voice.wav
```

## Recommended Voices by Type

### Professional/Natural Voices
- **Daniel** — Professional male voice (en_US)
- **Victoria** — Professional female voice (en_US)
- **Moira** — Natural female voice (en_IE)
- **Karen** — Clear female voice (en_AU)

### Friendly/Casual Voices
- **Samantha** — Friendly, energetic (en_US)
- **Flo** — Cheerful, upbeat
- **Tessa** — Pleasant, warm (en_ZA)

### Fun/Novelty Voices
- **Wobble** — Wobbly, funny voice
- **Bells** — Sounds like bells
- **Bubbles** — Bubbly, playful
- **Good** — Sounds like "Good" repeated
- **Bahh** — Sheep/goat sounds
- **Boing** — Boing sound effects
- **Jester** — Playful character voice
- **Rocko** — Rocky character voice
- **Superstar** — Confident/superstar voice
- **Whisper** — Whispered voice
- **Zarvox** — Retro/synthetic voice

### Multilingual Voices

**Spanish:**
- Montse, Mónica, Paulina

**French:**
- Jacques, Amélie

**German:**
- Tünde

**Italian:**
- Alice, Carmit

**Portuguese:**
- Joana, Luciana

**Russian:**
- Lesya

**Chinese:**
- Tingting, Meijia

**Indian:**
- Aman, Geeta, Lekha, Piya, Rishi, Soumya, Vani

**Japanese:**
- Kyoko

**Arabic:**
- Majed

**And many more!**

## How to Use Custom Voices in Your Voice Skill

Update your `voice_handler.py` to use a specific voice:

```python
# In the synthesize_speech function, add:
cmd = ['say', '-v', 'Victoria', '-o', str(output_file), text]
```

Or use the voice selector directly:

```bash
python3 ~/.claude/skills/voice-conversation/voice_selector.py --speak "Victoria" "Your response text here"
```

## Voice Selection Strategy

1. **Default**: Use Victoria (professional, clear)
2. **Casual conversations**: Use Samantha or Flo
3. **Fun/novelty**: Try Wobble, Bubbles, or Jester
4. **Other languages**: Pick language-specific voices above

## Set Your Preferred Voice

Create a `.voice_config` file:

```json
{
  "default_voice": "Victoria",
  "voice_map": {
    "professional": "Daniel",
    "friendly": "Samantha",
    "fun": "Wobble"
  }
}
```

Then reference it in voice_handler.py for context-aware voice selection.

## Testing New Voices

Best way to explore:

```bash
# Quick test of different voices
for voice in Victoria Samantha Wobble Rocko; do
  echo "Testing $voice:"
  python3 ~/.claude/skills/voice-conversation/voice_selector.py --test "$voice" "I am $voice"
done
```

Sources:
- [pyttsx3 · PyPI](https://pypi.org/project/pyttsx3/)
- [Changing voices in Pyttsx3 – python programming](https://pythonprogramming.altervista.org/changing-voices-in-pyttsx3/)
- [Using pyttsx3 — pyttsx3 2.6 documentation](https://pyttsx3.readthedocs.io/en/latest/engine.html)
