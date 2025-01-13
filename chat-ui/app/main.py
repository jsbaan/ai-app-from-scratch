import logging
import uuid
from typing import Annotated

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles

from pydantic_settings import BaseSettings

from starlette import status
from starlette.responses import RedirectResponse
from starlette.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import httpx

# Set up logging. This is useful for debugging and monitoring, especially on Azure where print statements aren't logged.
logger = logging.getLogger("uvicorn.error")


# A Pydantic Settings model that reads environment variables in a case-insensitive way and sets default values
# The default endpoints are used when running the uvicorn server directly. The Dockerfile overwrites them with env vars.
class Settings(BaseSettings):
    user_role: str = "user"
    assistant_role: str = "assistant"
    system_role: str = "system"
    system_message: str = "You are a helpful AI assistant."
    opening_message: str = (
        "Hi, how can I help you? I might take about 30 seconds for lengthy answers!"
    )
    lm_api_url: str = f"http://localhost:8000"
    db_api_url: str = f"http://localhost:8001"
    session_key: str = "top-secret-key"


# Load, convert and validate environment variables according to the schema above
settings = Settings()


# Creates the FastAPI app. This is the main entry point for the application, which we use to run the server.
app = FastAPI(
    title="User interface",
    description="A simple UI to chat with a language model. Depends on the database API to fetch and store chat histories, and the language model API to generate replies.",
)

# Jinja2 is templating engine that can "render" html templates, making them dynamic by filling in variables
# Load a directory that contains html templates
templates = Jinja2Templates(directory="app/templates")

# Mounts a directory with static files (in this case a css file to prettify our html) and serve at /static.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# A session cookie is a dict-like object that contains information about the user's session, like session_id. The user's
# browser stores the cookie and sends it with each request to the same hostname. Our sessions are encrypted and signed
# to prevent tampering. This middleware helps us by reading and decoding session cookies and exposing them in
# `request.session`. It sends the session cookie (including any changes we make to it, like adding a session_id) back
# to the browser in the response.
app.add_middleware(SessionMiddleware, secret_key=settings.session_key)


def get_session_id(request: Request):
    """
    This function is a "dependency" that we can use in our endpoints to get the session_id from the session cookie.
    It is invoked before the endpoint function itself is called and injects the session_id as argument.

    If no session ID exist, like for a new user, we generate a new one. This is a common pattern to identify users.
    """
    session_id = request.session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        request.session["session_id"] = session_id
    return session_id


@app.get("/")
def get_homepage(request: Request):
    """
    GET endpoint to render the homepage template.
    Args:
        request: contains information about the incoming request.

    Returns: the rendered homepage template.

    """
    return templates.TemplateResponse(request=request, name="home.html")


@app.post("/chats")
def create_chat(
    username: Annotated[str, Form()], session_id: str = Depends(get_session_id)
):
    """
    POST endpoint to create a new chat using a username and session_id.
    If the username already exists, the associated chat history is retrieved.

    Args:
        username: the username submitted to the HTML form of the chat to create or retrieve.
        session_id: the session id generated for the user.

    Returns: a redirect response to the chat page with the current chat_id as a query parameter.

    """
    create_chat_endpoint = f"{settings.db_api_url}/chats"
    get_chat_by_username_endpoint = f"{create_chat_endpoint}/username/{username}"

    # Call the db-api to create a new chat with the username, session_id and two initial messages
    response = httpx.post(
        create_chat_endpoint,
        json={
            "username": username,
            "session_id": session_id,
            "messages": [
                {
                    "role": settings.system_role,
                    "content": settings.system_message,
                    "session_id": session_id,
                },
                {
                    "role": settings.assistant_role,
                    "content": settings.opening_message,
                    "session_id": session_id,
                },
            ],
        },
    )
    chat = response.json()

    # If the username already exists, we fetch the chat history from the db-api
    if response.status_code == 400:
        # GET endpoints don't have a request body, and we do not want to pass the session_id in the URL for security.
        # Instead, we will use a custom HTTP header. A common name for this header is "X-Session-ID".
        chat = httpx.get(
            get_chat_by_username_endpoint, headers={"X-Session-ID": session_id}
        ).json()
    # Redirect the user to the chat page with the newly created or retrieved chat_id
    return RedirectResponse(
        url=app.url_path_for("get_chat_page", chat_id=chat["id"]),
        status_code=status.HTTP_302_FOUND,
    )


@app.get("/chats/{chat_id}")
def get_chat_page(
    request: Request, chat_id: str, session_id: str = Depends(get_session_id)
):
    """
    GET endpoint to render the chat page template with the chat history using the DB API
    Args:
        request: contains information about the incoming request.
        chat_id: the id of the chat to retrieve.
        session_id: the session id generated for the user.

    Returns: the rendered chat page template with the chat history.

    """

    # Retrieve chat history from the database api using the chat_id and session_id
    get_chat_by_id_endpoint = f"{settings.db_api_url}/chats/{chat_id}"
    chat = httpx.get(
        get_chat_by_id_endpoint, headers={"X-Session-ID": session_id}
    ).json()

    # Prettify the role names and filter out the system role messages
    prettify = {
        settings.user_role: chat["username"],
        settings.assistant_role: "JorisBot",
        settings.system_role: settings.system_role,
    }
    messages = [
        {"content": msg["content"], "role": prettify[msg["role"]]}
        for msg in chat["messages"]
        if msg["role"] != settings.system_role
    ]

    # Render and return the chat.html template with the chat id and history
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={"messages": messages, "chat_id": chat_id},
    )


@app.post("/generate/{chat_id}")
def create_generation(
    chat_id: str,
    prompt: Annotated[str, Form()],
    session_id: str = Depends(get_session_id),
):
    """
    POST endpoint to generate a response from the language model API and update the chat history with the DB API.
    Args:
        chat_id: the id of the chat to update.
        prompt: the user input submitted to the HTML form of the chat. We specify this with the `Annotated` type
         around the argument's type hint (str) using `Form()` as a metadata argument.
        session_id: the session id generated for the user.

    Returns: a redirect response to the chat page with the updated chat history.

    """
    # Call database api to add the user message to the postgres database
    create_chat_message_endpoint = f"{settings.db_api_url}/chats/{chat_id}/message"
    get_chat_by_id_endpoint = f"{settings.db_api_url}/chats/{chat_id}"
    httpx.post(
        create_chat_message_endpoint,
        json={"role": settings.user_role, "content": prompt, "session_id": session_id},
    ).json()

    # Retrieve full chat history from the database api using the chat_id and session_id
    chat = httpx.get(
        get_chat_by_id_endpoint, headers={"X-Session-ID": session_id}
    ).json()

    # Call language model api to generate text from the language model. We could have used langchain instead of httpx.
    try:
        headers = {"Content-Type": "application/json", "Authorization": "Bearer no-key"}
        generation = httpx.post(
            f"{settings.lm_api_url}/v1/chat/completions",
            headers=headers,
            timeout=30,
            json={
                "messages": chat["messages"],
            },
        ).json()
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Request to the LM API timed out. I'm using a maximum of 5 LM API replicas to avoid blowing up costs,"
            " so perhaps it's busy. Please wait a moment and retry.",
        )
    generation = generation["choices"][0]["message"]["content"]

    # # Call database api to add the generation to the postgres database
    httpx.post(
        create_chat_message_endpoint,
        json={
            "role": settings.assistant_role,
            "content": generation,
            "session_id": session_id,
        },
    )

    url = app.url_path_for("get_chat_page", chat_id=chat_id)
    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


if __name__ == "__main__":
    # This is useful for debugging and development, as we can connect to the pycharm debugger and set breakpoints.
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002, reload=True)
