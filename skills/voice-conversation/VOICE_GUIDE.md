# Voice Selection Guide

All voice samples are generated and saved to: `~/.agent-shared/voice/samples/`

## 👨 Professional Male Voices (For Claude/You)

**Test each:**
```bash
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Daniel
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Thomas
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Ralph
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Fred
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Albert
```

**Recommendations for Claude (male voice):**
- **Daniel** ⭐⭐⭐⭐⭐ - Most professional, clear, authoritative
- **Thomas** ⭐⭐⭐⭐ - Deep, warm, professional
- **Ralph** ⭐⭐⭐⭐ - Natural, friendly professional
- Fred - Good but more casual
- Albert - Clear but slightly robotic

## 👩 Professional Female Voices (For Mia)

**Test each:**
```bash
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Victoria
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Samantha
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Moira
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Karen
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Tessa
```

**Recommendations for Mia (female voice):**
- **Victoria** ⭐⭐⭐⭐⭐ - Professional, clear, friendly
- **Moira** ⭐⭐⭐⭐⭐ - Natural, warm, Irish accent
- **Samantha** ⭐⭐⭐⭐ - Energetic, friendly
- **Karen** ⭐⭐⭐⭐ - Clear, Australian accent
- Tessa - Pleasant but less distinctive

## 🎉 Fun/Character Voices (For Gemini or special occasions)

**Most interesting ones:**
```bash
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Wobble
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Jester
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Bubbles
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Whisper
python3 ~/.claude/skills/voice-conversation/voice_sampler.py --test Rocko
```

## 🌍 Multilingual Voices

For international contexts:
- **Jacques** - French (speaks naturally in French)
- **Amélie** - French Canadian
- **Kyoto** - Japanese
- **Tingting** - Mandarin Chinese
- **Majed** - Arabic

## 📋 How to Use

### Set Claude's voice (male):
```python
# In your voice_handler.py or config
DEFAULT_CLAUDE_VOICE = "Daniel"
```

### Set Mia's voice (female):
```python
DEFAULT_MIA_VOICE = "Victoria"
```

### Set Gemini's voice (neutral/fun):
```python
DEFAULT_GEMINI_VOICE = "Karen"  # or use fun voices for variety
```

### Or use in commands:
```bash
python3 ~/.claude/skills/voice-conversation/voice_handler.py --speak "Daniel" "Claude speaking"
python3 ~/.claude/skills/voice-conversation/voice_handler.py --speak "Victoria" "Mia speaking"
python3 ~/.claude/skills/voice-conversation/voice_handler.py --speak "Karen" "Gemini speaking"
```

## 📊 Voice Personality Chart

| Voice | Gender | Type | Formality | Best For |
|-------|--------|------|-----------|----------|
| Daniel | M | Professional | High | Claude (primary) |
| Thomas | M | Professional | High | Claude (alternative) |
| Victoria | F | Professional | High | Mia (primary) |
| Moira | F | Professional | Medium | Mia (alternative, warm) |
| Karen | F | Professional | Medium | Gemini (neutral) |
| Samantha | F | Professional | Medium | Gemini (friendly) |
| Wobble | ? | Fun | Low | Special moments |
| Jester | M | Character | Low | Entertainment |
| Whisper | ? | Atmospheric | Medium | Intimate/confidential |

## 🎯 Our Team Voice Setup

```
YOU (Luis):        👨 Male voice (Daniel) for Claude
                   👩 Female voice (Victoria) for Mia
                   🤖 Neutral voice (Karen) for Gemini

CLAUDE (Your AI):  Daniel - authoritative, professional
MIA (Assistant):   Victoria - friendly, professional
GEMINI (Helper):   Karen - clear, articulate
```

## 📁 Samples Location

All audio files are in: `~/.agent-shared/voice/samples/`

Each file is named: `{VoiceName}_{timestamp}.aiff`

Example: `Daniel_1768967045.aiff`

You can:
- Listen to them in Finder
- Copy them to send others
- Use them as reference for voice selection
- Delete old ones to save space (keep newest)

## Quick Selection Process

1. **Listen to professional male voices** - pick which Claude should sound like
2. **Listen to professional female voices** - pick which Mia should sound like
3. **Listen to a few fun voices** - for special moments or Gemini personality
4. **Update your config** with the chosen voices
5. **Done!** Your AI team now has consistent voices

---

**Happy listening! 🎧**
