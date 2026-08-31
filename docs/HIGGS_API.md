# Higgs TTS 3 (Boson AI) Integration Guide

The project provides first-class support for the Boson AI Higgs TTS 3 API.

## Configuration

1.  Copy `.env.example` to `.env` in the root of the project:
    ```bash
    copy .env.example .env
    ```
2.  Set your Boson API key:
    ```env
    BOSON_API_KEY=your_real_api_key_here
    ```
    *Do not hardcode or commit this file. The `.gitignore` prevents committing `.env` files.*
3.  On launch, the backend will verify if `BOSON_API_KEY` is present. If it is, the "Higgs TTS 3 (Boson AI)" model configuration will be set to `enabled=True` automatically.

---

## Zero-Shot Voice Cloning

When using Higgs TTS 3, you can perform zero-shot voice cloning by:
1.  Creating a Voice Profile in the WebUI.
2.  Uploading a short (5-30 seconds) reference audio file (`.wav` or `.mp3`).
3.  (Optional but recommended) Filling in the transcript of what the reference audio says in `ref_text`.
4.  Submitting a generation request.

**How it works under the hood:**
*   If a reference audio path is a local file, the `HiggsApiProvider` automatically structures a `multipart/form-data` request.
*   The reference audio is uploaded as a binary attachment (`ref_audio`) alongside the transcript (`ref_text`) and the input text.
*   This ensures instant voice replication without registering voice IDs on cloud servers.

---

## Inline Speech Control Tags

Higgs TTS 3 allows shaping prosody and emotional intensity directly inside the text input using standard tags.

### Supported Tags
*   **Emotion Modulation**:
    *   `<|emotion:affection|>` - Speaks with affectionate, warm tones.
    *   `<|emotion:enthusiasm|>` - Speaks with high excitement and energy.
    *   `<|emotion:confusion|>` - Speaks with uncertainty or hesitance.
*   **Prosody Manipulation**:
    *   `<|prosody:pause|>` - Inserts a natural pause at that position.

**Example Input:**
```text
今日もお疲れさまでした。<|emotion:affection|>無理しないでくださいね。
```
These tags can be quickly clicked and inserted at the text cursor using the shortcut panel in the WebUI.

---

## Manual Verification & Testing (Higgs API)

> [!IMPORTANT]
> The automated backend smoke test (`run_smoke_test.bat`) only exercises the `DummyProvider`. 
> Higgs API integration requires a valid `BOSON_API_KEY` and is **not** covered by the offline smoke test.

To manually test the Higgs API configuration:
1. Ensure `BOSON_API_KEY` is configured in your `.env` file.
2. Launch the backend server (`start_backend.bat`).
3. Run the following command in command prompt (or PowerShell) to verify immediate speech synthesis:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/speak ^
     -H "Content-Type: application/json" ^
     -d "{\"text\": \"Hello, Higgs. This is a manual test.\", \"params\": {}}"
   ```
4. Confirm that the response status is `"succeeded"` and plays back correctly in your audio player.

---

## Verified Providers (Verification Status)

The Higgs TTS 3 integration has been verified through the following tests:
*   **DummyProvider smoke test**: **PASSED** (automated verification tool generated beep output).
*   **Higgs TTS 3 normal generation**: **VERIFIED SUCCESSFULLY** (manually verified speech output through cloud endpoints).
*   **Higgs TTS 3 voice cloning with reference audio**: **VERIFIED SUCCESSFULLY** (manually verified voice clone by uploading WAV reference files).

### Zero-Shot Voice Cloning Recommendations
1.  **BOSON_API_KEY**: Must be configured in `.env` (system loads it on startup to activate the model).
2.  **Reference Audio & Text**: For optimal and stable zero-shot voice cloning quality, providing a clean **reference audio** (5–30 seconds, wav/mp3 format) **AND** the corresponding **ref_text** transcript is highly recommended.

---

## Troubleshooting Guide

### 1. Missing `BOSON_API_KEY`
*   **Symptom**: Backend logs show `ValueError: Missing BOSON_API_KEY...` or frontend shows authentication errors.
*   **Fix**: Check if `.env` exists in the root folder, contains `BOSON_API_KEY=your_key`, and that uvicorn was restarted to pick up changes.

### 2. Invalid API Base
*   **Symptom**: Connection timeout or DNS resolution failure.
*   **Fix**: Verify your model configuration in the WebUI. The default API Base should be `https://api.boson.ai/v1/audio/speech`. Make sure there are no typos in the URL.

### 3. Missing `ref_audio`
*   **Symptom**: Cloud response sounds like a generic default voice instead of the target voice clone.
*   **Fix**: Verify that the uploaded reference audio exists in the Voice Profile list and shows "🎤 Cloned Voice" in the UI. Make sure the file exists in `data/reference/profile_{id}.wav` (or other supported formats).

### 4. Wrong `ref_text`
*   **Symptom**: Cloned voice output sounds robotic, stuttered, or drops words.
*   **Fix**: The `ref_text` must be a verbatim transcript of what is spoken in the reference audio. Ensure it matches exactly (including filler words, stutters, and punctuation).

### 5. Unsupported Audio Format
*   **Symptom**: Multipart upload fails with `400 Bad Request` or backend complains of decoding errors.
*   **Fix**: Ensure your reference audio is one of the supported formats: `wav`, `mp3`, `opus`, `pcm`, or `flac`. Avoid high-bitrate multi-channel audio (prefer mono 16kHz or 24kHz files).
