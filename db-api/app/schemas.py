"""
This file contains the Pydantic schemas that define what our API endpoints expect and return.

The schemas are used to validate the data in requests to the API and responses from it, and to generate documentation.

"""

from typing import List
from uuid import UUID

from pydantic import BaseModel


class MessageCreate(BaseModel):
    """Pydantic schema that defines the structure for creating a new chat message."""

    content: str
    role: str
    session_id: str


class Message(MessageCreate):
    """Pydantic schema that defines the structure for a chat message fetched from the database."""

    id: UUID
    owner_id: UUID

    class Config:
        """Read data even if it is not a dict, but an ORM model (or any other arbitrary object)."""

        from_attributes = True


class ChatCreate(BaseModel):
    """Pydantic schema that defines the structure for creating a new chat."""

    username: str
    messages: List[MessageCreate] = []
    session_id: str


class Chat(ChatCreate):
    """Pydantic schema that defines the structure for a chat fetched from the database."""

    id: UUID
    messages: List[Message] = []

    class Config:
        """Read data even if it is not a dict, but an ORM model (or any other arbitrary object)."""

        from_attributes = True
