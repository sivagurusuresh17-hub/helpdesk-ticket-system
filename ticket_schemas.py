from pydantic import BaseModel
from typing import Optional


class TicketCreate(BaseModel):
    title: str
    description: str
    priority: str = "MEDIUM"
    category: Optional[str] = None
    created_by: int