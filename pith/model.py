from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class User(BaseModel):
    id: Optional[int] = None
    created: Optional[datetime] = None
    doreset: Optional[bool] = None
    confirmed: Optional[bool] = None
    active: Optional[bool] = None
    timezone: Optional[str] = None
    role: Optional[str] = None
    # Begin PII
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
