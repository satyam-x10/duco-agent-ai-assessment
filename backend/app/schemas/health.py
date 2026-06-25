from pydantic import BaseModel


class HealthSchema(BaseModel):
    """Pydantic schema representing the application health status response."""
    status: str
    service: str
    version: str
