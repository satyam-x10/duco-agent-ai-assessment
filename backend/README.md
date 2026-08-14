# DuCO-Agent: Backend Orchestrator

The backend component exposes FastAPI endpoints and a typed asynchronous multi-agent workflow. Gemini is an optional inference dependency; deterministic extraction and payment logic remain ordinary testable Python services.

## Folder Structure

*   **`app/`**: Contains core FastAPI framework configuration and routers.
    *   **`api/`**: API route configurations and versioning structures.
    *   **`core/`**: Application builder, logging initializers, and exception handlers.
    *   **`config/`**: Environment variable loader using Pydantic Settings.
    *   **`dependencies/`**: Global parameter injections.
    *   **`middleware/`**: Request filters and logging.
    *   **`schemas/`**: Pydantic serialization models.
*   **`main.py`**: Entrypoint script to run the API web server.
*   **`agents/`**: Specialist AI agent definitions and persona files.
*   **`tools/`**: Functional tools (OCR, parsers, calculators).
*   **`workflows/`**: Run schedules coordinating multi-agent actions.
*   **`services/`**: Core integrations (Google ADK configurations, Gemini APIs).
*   **`models/`**: Shared domain models.
*   **`mock_data/`**: Standard patient mock records.
*   **`outputs/`**: Workspace folder for write-out artifacts.
*   **`tests/`**: Suite for unit and route verification checks.

---

## Development Setup

### 1. Prerequisites
Ensure you have Python 3.10+ installed on your system.

### 2. Configure Virtual Environment
From the `backend/` directory, create and activate a Python virtual environment:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
Install the required packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` if not already present:
```bash
cp .env.example .env
```

### 5. Launch the Server
Start the development server using the entrypoint script:
```bash
python main.py
```
Alternatively, you can run:
```bash
uvicorn main:app --reload
```

---

## API Endpoints

*   **Root endpoint**: `GET http://localhost:8000/` (returns a welcoming message)
*   **Health check endpoint**: `GET http://localhost:8000/api/v1/health` (returns service statuses)
*   **API documentation**:
    *   Swagger UI: `GET http://localhost:8000/docs`
    *   ReDoc UI: `GET http://localhost:8000/redoc`
