from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AuthUser:
    id: str
    email: str
    name: str
    password_hash: str
    role: str = "user"
    created_at: datetime = field(default_factory=datetime.utcnow)
