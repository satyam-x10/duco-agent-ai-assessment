# DuCO-Agent: Backend Orchestrator

The backend component of DuCO-Agent is responsible for exposing enterprise-grade REST APIs using FastAPI, and orchestrating multi-agent workflows using the Google Agent Development Kit (ADK) and Gemini models.

## Folder Structure

*   **`app/`**: Contains FastAPI routers, middleware, custom exception handlers, and the main application initialization entry (`main.py`).
*   **`agents/`**: Holds custom implementations of specialist AI agents (e.g., Intake, Medical Coding, COB reasoning, Reviewer).
*   **`tools/`**: Contains functional tools exposed to the agents (e.g., OCR utilities, PDF parsers, medical code lookup services).
*   **`workflows/`**: Handles the execution flow and state management for multi-agent collaboration runs.
*   **`services/`**: Integration layers with external services, databases, and Gemini LLM configurations.
*   **`models/`**: Defines Pydantic data schemas representing input payloads, intermediate states, and API responses.
*   **`mock_data/`**: Standardized mock databases of medical records and insurance policies for offline testing.
*   **`outputs/`**: Workspace for writing agent-generated artifacts, such as cost flow diagrams, pre-auth PDF letters, and audio summaries.
*   **`tests/`**: Test suite containing unit tests for tools/agents and integration tests for workflows.

## Development Setup

*Instructions on setting up a virtual environment (`venv`) and launching the FastAPI development server will be provided upon API initialization.*
