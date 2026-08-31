# Desktop Pet TTS Integration Guide

For external systems, desktop pets, or AI assistants, the backend provides a simplified, synchronous-like interface to convert text into speech immediately.

## Simple Integration (`/api/speak`)

Instead of enqueuing and polling (standard `/api/generate` flow), desktop pets should make a single HTTP POST request to `/api/speak`.

### Verified Request / Response Payload Examples

#### 1. Higgs TTS 3 Normal Speech Generation
**Request Payload:**
```json
{
  "text": "Hello, this is a manual verification of Higgs normal speech synthesis via the speak endpoint.",
  "model_id": 2,
  "params": {}
}
```

**Response Payload:**
```json
{
  "job_id": "f65feef12e0b4295aa8cbfca7f5ddd6d",
  "status": "succeeded",
  "audio_url": "/api/audio/f65feef12e0b4295aa8cbfca7f5ddd6d.mp3",
  "duration": 4.717116
}
```

#### 2. Higgs TTS 3 Zero-Shot Voice Cloning (with Voice Profile)
**Request Payload:**
```json
{
  "text": "Hello, this is a zero-shot voice clone synthesis manual verification test using Higgs API.",
  "profile_id": 2,
  "params": {}
}
```

**Response Payload:**
```json
{
  "job_id": "97d7f8647bd544cca13d9d87c62e709a",
  "status": "succeeded",
  "audio_url": "/api/audio/97d7f8647bd544cca13d9d87c62e709a.mp3",
  "duration": 12.131668
}
```

### Parameter Reference

*   `text` (Required): String payload.
*   `profile_id` (Optional): ID of the voice profile. If provided, the API automatically fetches the associated model ID and any reference voice cloning assets.
*   `model_id` (Optional): Explicit model configuration ID.
*   `params` (Optional): Custom parameters to merge (overwrites model defaults).

### Response Fields

*   `job_id`: Generated UUID for tracking.
*   `status`: `"succeeded"` or `"failed"`.
*   `audio_url`: Playback API endpoint path. E.g., `http://127.0.0.1:8000/api/audio/4020a6a5ee5b4b1a823023e32e8b0933.wav`.
*   `duration`: Exact length of the generated audio in seconds. Useful for controlling mouth-flapping/blinking animations of the desktop pet!

### Python Client Example

Here is a Python client script for a desktop pet:

```python
import httpx
import playsound # pip install playsound

SERVER_URL = "http://127.0.0.1:8000"

def pet_speak(text: str, voice_profile_id: int):
    payload = {
        "text": text,
        "profile_id": voice_profile_id
    }
    
    # Request immediate TTS
    response = httpx.post(f"{SERVER_URL}/api/speak", json=payload, timeout=30.0)
    if response.status_code == 200:
        data = response.json()
        if data["status"] == "succeeded":
            audio_url = f"{SERVER_URL}{data['audio_url']}"
            duration = data["duration"]
            print(f"Speaking for {duration} seconds...")
            
            # Download and play
            audio_response = httpx.get(audio_url)
            with open("temp_speak.wav", "wb") as f:
                f.write(audio_response.content)
            
            playsound.playsound("temp_speak.wav")
        else:
            print("Failed to generate voice:", data.get("error"))
```
