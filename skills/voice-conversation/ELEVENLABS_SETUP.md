# ElevenLabs Integration Setup

## Quick Start

### 1. Sign Up (Free)
- Go to https://elevenlabs.io
- Sign up for free account
- Free tier: 10,000-20,000 characters/month (~20 minutes of speech)

### 2. Get Your API Key
1. Log in to ElevenLabs
2. Go to **Settings** → **API Keys**
3. Copy your API key (starts with `sk_`)

### 3. Create `.env` File
Create a `.env` file in your project directory with:

```
ELEVENLABS_API_KEY=sk_your_actual_key_here
```

Or set as environment variable:
```bash
export ELEVENLABS_API_KEY=sk_your_actual_key_here
```

### 4. Install Python Dependencies
```bash
pip install requests python-dotenv
```

### 5. Test It
```bash
python3 voice_handler.py --speak "Let me help you build that for you"
```

If ElevenLabs key is configured, it will use that. Otherwise falls back to native OS text-to-speech.

## Voice Selection

### Natural Female Voices (for Mia)
- **Bella** (Default) - Warm, friendly, natural
- **Rachel** - Clear, professional, articulate
- **Charlotte** - Soft, warm, engaging
- **Aria** - Expressive, dynamic, engaging

### Professional Male Voices (for Claude)
- **Josh** - Deep, warm, professional
- **Sam** - Standard, clear, reliable
- **Michael** - Authoritative, professional

### Fun/Unique Voices
- **Bill** - Warm, storyteller voice
- **Gigi** - Young, energetic female
- **Callum** - British accent, male

## How to Test Before Committing

1. **List available ElevenLabs voices:**
   ```bash
   python3 -c "
   import json
   import requests
   from dotenv import load_dotenv
   from pathlib import Path
   import os

   load_dotenv(Path.home() / '.env')
   api_key = os.getenv('ELEVENLABS_API_KEY')

   if api_key:
       headers = {'xi-api-key': api_key}
       resp = requests.get('https://api.elevenlabs.io/v1/voices', headers=headers)
       voices = resp.json()['voices']
       for v in voices[:15]:
           print(f\"{v['name']:20} - {v['voice_id']}\")
   "
   ```

2. **Test a specific voice:**
   ```bash
   python3 voice_handler.py --speak "Let me help you build that for you" --voice-id VOICE_ID_HERE
   ```

3. **Or stick with native OS voices** (free, no credits used):
   ```bash
   python3 voice_handler.py --speak "Test text" --use-macos
   ```

## Fallback Behavior

If ElevenLabs API is down or you run out of credits, the system automatically falls back to native OS text-to-speech. No crashes, no interruptions.

## Credit Estimation

For your use case (quick voice responses):
- Average response: ~50 characters = 50 credits
- Free tier: 10,000-20,000 credits/month
- Estimate: 200-400 responses per month

For production use, the $5/month plan gives 100,000 characters/month, which is plenty.

## Configuration Priority

1. **If ELEVENLABS_API_KEY set in ~/.env** → Use ElevenLabs (natural sound)
2. **If missing/API error** → Fall back to macOS `say` (instant, free)
3. **You can force either:**
   - `--use-elevenlabs` flag (must have API key)
   - `--use-macos` flag (ignore API key, always use say)

## Environment Variables

Store in your `.env` file (not committed to git):

```
# Required for ElevenLabs
ELEVENLABS_API_KEY=sk_xxx_your_key_xxx

# Optional - Set agent-specific voice ID
ELEVENLABS_VOICE_ID=your_voice_id_here
```

Or export directly:
```bash
export ELEVENLABS_API_KEY=sk_xxx_your_key_xxx
export ELEVENLABS_VOICE_ID=your_voice_id_here
```
