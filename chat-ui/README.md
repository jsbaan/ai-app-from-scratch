Simple web-based user interface built with FastAPI that allows users to start or continue a chat with a language model. 

The UI makes HTTP requests to the database API and language model API, so make sure these are running.

# Running the server
There are several ways to run the UI. We will make it available at http://localhost:8002.

## Python server
By default, the UI expects the LM-API to run at localhost:8000 and the DB-API at localhost:8001. To run the Python server manually, first create a virtual environment and install the packages in `requirements.txt`.


To start UI as single Uvicorn dev server with default (local) host ip address on host machine's port 8001:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8002
```

Or as Gunicorn process manager with 4 uvicorn worker processes. Available at  http://localhost:8001.
```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8002
```

## Docker container
Docker containers are completely isolated they have their own localhost. This means that if we run the UI in a Docker container, it cannot reach the LM and DB API servers running on our computer's localhost: they all need to be on the same private network.

The UI can reach the servers by their container names which Docker DNS resolves to their container IP addresses. We pass the hostnames as environment variables and can publish the UI's container port 80 to our host machine's port 8001.

```bash
docker build -t chat-ui-image .
docker run -d --name chat-ui --network chat-net --publish 8002:80 --env LM_API_URL=<lm api container name> --env DB_API_URL=<db api container name> chat-ui-image
```

## Docker Compose
To run the API with Docker Compose, see [compose.yml](../compose.yml)