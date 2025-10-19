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

class Event(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
    summary: Optional[str] = None
    category: Optional[str] = None

class EventsResponse(BaseModel):
    events: List[Event]
