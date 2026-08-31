# TTS WebUI Workbench Backend

FastAPI application providing unified TTS generation, job queueing, profile assets storage, and a simplified synchronous interface for external desktop pets.

## Quick Start (Manual)

### 1. Requirements
*   Python 3.11+
*   pip

### 2. Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate.bat
pip install -r requirements.txt
```

### 3. Running
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## REST API Swagger
Navigate to `http://127.0.0.1:8000/docs` while the server is running to view the interactive OpenAPI schema and test endpoints.
