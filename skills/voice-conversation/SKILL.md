---
name: voice-conversation
description: Real-time voice conversation - record, transcribe, speak. Optimized for M2 Mac
agents: [claude, mia, gemini]
type: voice-io
tags: [voice, speech-to-text, text-to-speech, conversation, realtime]
---

# Voice Conversation Skill

**MVP**: Record your voice, transcribe with Whisper, generate TTS responses. All native M2 Mac.

## Requirements

### Install dependencies:
```bash
# Audio recording
brew install sox

# Speech-to-text (Whisper)
pip install openai-whisper

# Text-to-speech (optional, for pyttsx3)
pip install pyttsx3

# Or use native macOS `say` command (built-in)
```

## Usage

### Record Audio
```bash
python3 voice_handler.py --record --duration 10
```
Records 10 seconds of audio, saves to your configured audio directory.

### Transcribe Audio
```bash
python3 voice_handler.py --transcribe path/to/audio.wav --model base
```
Models: `tiny`, `base`, `small`, `medium`, `large`
- Larger = more accurate but slower
- Start with `base` for optimal balance

### Text-to-Speech
```bash
python3 voice_handler.py --speak "Hello, how can I help you?"
```
Generates speech and saves to your configured audio directory.

### Play Audio
```bash
python3 voice_handler.py --play path/to/audio.wav
```
Uses native audio playback (`afplay` on macOS).

### Full Cycle (Record → Transcribe)
```bash
python3 voice_handler.py --cycle --duration 5
```

## Shared Storage

**Audio files**: Configured in environment or defaults to system audio directory
- Format: `audio_<unix_timestamp>.wav` or `tts_<unix_timestamp>.wav`

**Transcripts**: Latest transcript stored as JSON
```json
{
  "timestamp": "2026-01-20T21:45:30.123456",
  "audio_file": "path/to/audio_1705800330.wav",
  "text": "User's spoken message",
  "model": "base",
  "language": "en"
}
```

**Responses**: Latest response stored as JSON
```json
{
  "timestamp": "2026-01-20T21:45:35.123456",
  "text": "Agent's text response",
  "output_file": "path/to/tts_1705800335.wav",
  "method": "audio-synthesis-backend"
}
```

## Agent Voice Configuration

Each agent has a distinct, personality-matched voice:

**Claude (Josh)**
- Voice ID: `ZoiZ8fuDWInAcwPXaVeq`
- Tone: Deep, warm, professional
- Use: `ELEVENLABS_VOICE_ID="ZoiZ8fuDWInAcwPXaVeq" python3 voice_handler.py --speak "..."`

**Mia (ChatGPT)**
- Backend: OpenAI ChatGPT API
- Tone: Precise, structured, analytical
- Role: Validation-first reasoning with mirror reflection
- Use: ChatGPT integration via API (configure OPENAI_API_KEY in environment)

**Gemini (Analytical)**
- Voice ID: `EGPLqH9Wz2tNLu58EJVR`
- Tone: Clear, articulate, analytical
- Use: `ELEVENLABS_VOICE_ID="EGPLqH9Wz2tNLu58EJVR" python3 voice_handler.py --speak "..."`

## Audio-First Workflow Pattern

**Recommended approach for agent responses in multi-modal sessions:**

### The Pattern: Voice Command → Page Break → Normal Text

1. **Voice Command** (1-2 lines, fires immediately)
   ```bash
   ELEVENLABS_VOICE_ID="ZoiZ8fuDWInAcwPXaVeq" python3 voice_handler.py --speak "I'll help with that. One moment."
   ```
   - Audio plays right away
   - User hears agent presence immediately

2. **Page Break** (visual separation)
   - Signals transition from voice to text
   - Gives user time to listen while reading begins

3. **Normal Text Response** (full detailed answer)
   - Complete reasoning and explanation
   - Arrives while or after audio completes
   - User has full context in text form

### Example: Mia Agent (ChatGPT)
```
ELEVENLABS_VOICE_ID="XB0fDUnXU5powFXDhCwa" python3 voice_handler.py --speak "Validating your request. Structure looks correct."

---

**Full Response:**
Your request has been validated against the following criteria:
- API keys configured correctly
- Voice IDs match expected format
- Audio fallback ready if ElevenLabs unavailable

Proceeding with implementation.
```

### Example: Claude Agent (Analytical)
```
ELEVENLABS_VOICE_ID="ZoiZ8fuDWInAcwPXaVeq" python3 voice_handler.py --speak "I found three approaches. The first is optimal."

---

**Full Response:**
After analyzing your requirements, here are the options:

1. **Recommended**: Direct API integration
   - Pros: Minimal latency, full control
   - Cons: Requires manual token management

2. Alternative: Wrapper library approach
   - Pros: Abstraction, easier debugging
   - Cons: Extra layer of indirection

3. Fallback: Shell script wrapper
   - Pros: No dependencies
   - Cons: Limited error handling

I recommend option 1 based on your performance requirements.
```

### Benefits
- **Immediate presence** — User hears agent within 1 second
- **Never forgotten** — Audio fires first, not added as afterthought
- **Natural flow** — Voice + text arrive together, complementary
- **Works for all agents** — Claude, Mia, Gemini all follow same pattern
- **Respects user attention** — Short audio summary, full text for deep reading

## How Agents Use It

**Claude/Mia/Gemini workflow (audio-first pattern):**
1. Receive user input (via Whisper transcription or direct message)
2. **Fire audio summary immediately** (1-2 lines): `voice_handler.py --speak "..."`
3. Generate detailed response text
4. Send full text response to chat/console
5. Audio plays while user reads detailed response

This ensures immediate vocal presence while text reasoning completes in parallel.

## Cross-Platform Optimization

- Uses native OS audio frameworks where available
- CPU-efficient transcription via Whisper (optional GPU acceleration)
- Low latency: record → transcribe → respond in < 30 seconds
- Minimal external dependencies (pip/environment-based)

## Next Steps

- [ ] Real-time streaming transcription (not batch)
- [ ] Custom voice profiles (different speakers)
- [ ] Wake word detection ("Hey Claude")
- [ ] Noise filtering before transcription
- [ ] Integration with camera-capture for context-aware responses
- [ ] Voice activity detection (auto-stop recording on silence)
