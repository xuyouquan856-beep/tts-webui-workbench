# TTS WebUI Workbench API Documentation

This backend is built on FastAPI and exposes REST endpoints under the `/api` prefix.

## Endpoints Summary

### 1. Health & Server Status
*   **GET `/api/health`**
    *   Returns server status and configurations.
    *   Response:
        ```json
        {
          "status": "healthy",
          "boson_api_key_configured": true,
          "database_url": "sqlite:///..."
        }
        ```

### 2. Providers List
*   **GET `/api/providers`**
    *   Lists the active backend provider names.
    *   Response: `["dummy", "higgs_api", "local_http", "local_command", "piper"]`

### 3. Model Management
*   **GET `/api/models`**: List all models.
*   **POST `/api/models`**: Register a new model configuration.
*   **PUT `/api/models/{id}`**: Update an existing model.
    *   Request JSON:
        ```json
        {
          "name": "My Local Model",
          "provider_type": "local_command",
          "api_base": null,
          "model_name": null,
          "command_template": "python infer.py --text \"{text}\" --out \"{output_path}\"",
          "model_path": "models/model.pth",
          "output_format": "wav",
          "enabled": true,
          "params_json": "{}"
        }
        ```

### 4. Voice Profiles
*   **GET `/api/profiles`**: List all profiles.
*   **POST `/api/profiles`**: Register a new profile.
*   **POST `/api/profiles/{id}/upload-reference`** (and `/api/profiles/{id}/reference-audio`):
    *   Uploads reference audio via `multipart/form-data` with `file` form-field.
    *   Saves the audio safely inside `data/reference/profile_{id}.ext` and registers the path in SQLite.

### 5. Task Queue & Audio Generation
*   **POST `/api/generate`**
    *   Enqueues a TTS request in the asynchronous sequential queue. Returns a `job_id`.
    *   Request Body:
        ```json
        {
          "text": "Hello, world!",
          "model_id": 1,
          "profile_id": null,
          "params": {},
          "return_format": "wav"
        }
        ```
    *   Response: `{"job_id": "abc123xyz...", "status": "queued"}`

*   **GET `/api/jobs/{id}`**
    *   Retrieves the status of an enqueued job (`queued`, `running`, `succeeded`, `failed`). Includes `audio_url`, `duration`, and `error_message` if applicable.

*   **GET `/api/history`**
    *   Returns the complete history list of all jobs, sorted descendingly.

*   **GET `/api/audio/{filename_or_job_id}`**
    *   Streams a generated file back as binary output (supports both file names and Job IDs).

### 6. Simplified Desktop Pet Interface
*   **POST `/api/speak`**
    *   Blocks and returns audio generation details immediately. Ideal for desktop pets and CLI integrations.
    *   Request JSON:
        ```json
        {
          "text": "Hello, master!",
          "profile_id": 1,
          "params": {}
        }
        ```
    *   Response:
        ```json
        {
          "job_id": "1abc2def...",
          "status": "succeeded",
          "audio_url": "/api/audio/1abc2def.wav",
          "duration": 1.45
        }
        ```
