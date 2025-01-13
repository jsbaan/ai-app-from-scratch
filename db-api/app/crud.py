""" This module contains the CRUD (Create, Read, Update, Delete) operations for the database. """

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models, schemas


def create_chat(db: Session, chat: schemas.ChatCreate):
    """Creates a new chat object in the database with the username and list of messages from the request."""

    # Check if the chat already exists in the database.
    db_chat = get_chat_by_username(
        db, username=chat.username, session_id=chat.session_id
    )
    if db_chat:
        raise HTTPException(
            status_code=400, detail=f"Chat with username {chat.username} already exists"
        )

    # If the chat does not exist, create a new SQLAlchemy model instance with the username from the request.
    db_chat = models.Chat(username=chat.username, session_id=chat.session_id)

    # Add the instance to the database session and commit to store.
    db.add(db_chat)
    db.commit()

    # Refresh to get freshly created db object and its auto-generated id from the database.
    db.refresh(db_chat)

    # Create messages that were included in the request and link them to the new chat
    for message in chat.messages:
        create_chat_message(db, db_chat.id, message)
    return db_chat


def create_chat_message(db: Session, chat_id: str, chat_message: schemas.MessageCreate):
    """Creates new message object in the database with message content and role from the request for a chat_id."""

    # Create a SQLAlchemy model instance with the message content and role from the request.
    db_message = models.Message(**chat_message.dict(), owner_id=chat_id)

    # Add the instance to the database session and commit to store.
    db.add(db_message)
    db.commit()

    # Fetch new message from the db, including auto-generated id.
    db.refresh(db_message)
    return db_message


def get_chat(db: Session, chat_id: str, session_id: str):
    """Retrieves a chat object from the database by its id."""
    return (
        db.query(models.Chat)
        .filter(models.Chat.id == chat_id, models.Chat.session_id == session_id)
        .first()
    )


def get_chat_by_username(db: Session, username: str, session_id: str):
    """Retrieves a chat object from the database by its username."""
    return (
        db.query(models.Chat)
        .filter(models.Chat.username == username, models.Chat.session_id == session_id)
        .first()
    )
