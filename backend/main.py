import uvicorn
from app.core.app import get_app

app = get_app()


@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint welcoming developers to the DuCO-Agent API."""
    return {
        "message": "Welcome to the DuCO-Agent API. Workspace initialized successfully."
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
