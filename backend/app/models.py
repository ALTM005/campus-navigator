from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any

class OfficeIn(BaseModel):
    name: str
    building: str
    room: Optional[str] = None
    lat: float
    lng: float
    url: Optional[HttpUrl] = None
    confidence: float = Field(default=1.0, ge=0, le=1.0)

class Office(OfficeIn):
    id: int
    updated_at: int

class EventsResponse(BaseModel):
    events: List[Dict[str, Any]]