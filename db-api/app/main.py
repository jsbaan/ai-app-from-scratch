from fastapi import Depends, FastAPI, Request, HTTPException
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from . import crud, models, schemas
from .database import SessionLocal, engine
import logging

# Set up logging. This is useful for debugging and monitoring, especially on Azure where print statements aren't logged.
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """This function's code before yield executes before the app starts. Code after yield executes after it stops."""
    logger.info("Creating database tables if they don't exist yet...")

    # Create db tables based on models.py. In production, use alembic for creating tables and doing migrations.
    models.Base.metadata.create_all(bind=engine)

    yield


# Create the FastAPI app, the main entry point for our api that will be served by the uvicorn server.
app = FastAPI(
    title="Database API",
    description="A simple API to store and fetch chats and their messages. Depends on a PostgreSQL server. ",
    lifespan=lifespan,
)


def get_db():
    """
    Each request to our API's endpoints needs its own database session.
    We handle this using "dependency injection" and pass this function as Depend argument in each endpoint.
    This makes sure each request gets its own db session and the session is closed after the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/chats", response_model=schemas.Chat)
async def create_chat(chat: schemas.ChatCreate, db: Session = Depends(get_db)):
    """
    POST endpoint to create a new chat in the database with the username and messages in the request body.
    Args:
        chat: request body with a username, list of messages and session_id.
        db: a "Dependency" that creates and closes a database session for each request.

    Returns: the chat history as a dict that will be validated by the `Chat` response_model.

    """
    db_chat = crud.create_chat(db, chat)
    return db_chat


@app.get("/chats/{chat_id}", response_model=schemas.Chat)
async def get_chat_by_id(request: Request, chat_id: str, db: Session = Depends(get_db)):
    """
    GET endpoint to retrieve a chat by its id from the postgres database.
    Args:
        request: the request object that contains the session_id in the headers.
        chat_id: the id of the chat to retrieve.
        user_session: information about the session of the user making the request.
        db: a "Dependency" that creates and closes a database session for each request.

    Returns: the chat history as a dict that will be validated by the `Chat` response_model.
    """
    # Get the session_id from the custom request headers that we set in the UI.
    session_id = request.headers.get("X-Session-ID")

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    return crud.get_chat(db, chat_id, session_id)


@app.get("/chats/username/{username}", response_model=schemas.Chat)
async def get_chat_by_username(
    request: Request, username: str, db: Session = Depends(get_db)
):
    """
    GET endpoint to retrieve a chat by its username from the postgres database.
    Args:
        request: the request object that contains the session_id in the headers.
        username: the username from to the chat to retrieve.
        user_session: information about the session of the user making the request.
        db: a "Dependency" that creates and closes a database session for each request.

    Returns: the chat history as a dict that will be validated by the `Chat` response_model.
    """
    # Get the session_id from the custom request headers that we set in the UI.
    session_id = request.headers.get("X-Session-ID")

    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required")
    return crud.get_chat_by_username(db, username, session_id)


@app.post("/chats/{chat_id}/message", response_model=schemas.Message)
async def create_chat_message(
    chat_id: str, message: schemas.MessageCreate, db: Session = Depends(get_db)
):
    """
    POST endpoint to add a new message to an existing chat in the database.
    Args:
        chat_id: the id of the chat to add the message to.
        message: the message content, role and session_id in the request body.
        db: a "Dependency" that creates and closes a database session for each request.

    Returns: the message as a dict that will be validated by the `Message` response_model.
    """
    return crud.create_chat_message(db, chat_id, message)


if __name__ == "__main__":
    # This is useful for debugging and development, as we can connect to the pycharm debugger and set breakpoints.
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
