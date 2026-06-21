from __future__ import annotations

import time
from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class AiChatMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class AiChatSession:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = "새 대화"
    context_mode: str = "general"
    messages: list[AiChatMessage] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
