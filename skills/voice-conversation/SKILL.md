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

1. **Fire audio summary first** (1-2 lines concisely via voice_handler.py)
   - User hears immediate vocal confirmation
   - No waiting for reasoning to complete

2. **Send full text response** in parallel
   - Detailed explanation lands while audio plays
   - User can read or listen, both available simultaneously

3. **Benefits:**
   - Immediate presence confirmed via voice
   - Audio is never forgotten (fires first, not last)
   - Text and audio flow together naturally
   - Works consistently across all three agents

**Example flow:**
```bash
# Agent receives request → fires audio summary immediately
export VOICE_ID="your_voice_id_here"  # Set agent-specific voice ID
python3 voice_handler.py --speak "I'll analyze that. One moment."

# While audio plays, full response lands in text
# Full detailed analysis sent to console/chat output
```

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
