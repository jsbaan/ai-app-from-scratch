"""
This module contains the SQLAlchemy models mapped to database tables. These models define the structure of the tables.

We will define one table to contain all chats and one table to contain all messages. The Chat table will have a
one-to-many relationship with the Message table.

Note that these SQLAlchemy models are different from the Pydantic schemas in schemas.py that validate, convert
and document request and response data in our API.

"""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class Chat(Base):
    """
    Represents a chat session. Each chat has a unique username and is associated with one or more messages.
    This table is used to store chat metadata.
    """

    __tablename__ = "chats"

    # Unique identifier for each chat that will be generated automatically. This column is the primary key.
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Username associated with the chat. Index is created for faster lookups by username.
    username = Column(String, index=True)

    # Session ID associated with the chat. Used to "scope" chats, i.e., users can only access chats from their session.
    session_id = Column(String, index=True)

    # The relationship function links the Chat model to the Message model.
    # The back_populates flag creates a bidirectional relationship.
    messages = relationship("Message", back_populates="owner")


class Message(Base):
    """
    Represents individual message in a chat. Each message is linked to a specific
    chat session and stores its content along with the sender's role.
    """

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(String, index=True)
    role = Column(String, index=True)

    # Session ID that links this message to a specific session.
    session_id = Column(String, index=True)

    # Foreign key linking this message to a specific chat session. References the id column in the Chat table.
    owner_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"))

    # The relationship function links the Message model to the Chat model.
    owner = relationship("Chat", back_populates="messages")
