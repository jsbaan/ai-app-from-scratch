# Database API
A Python API built with FastAPI and SQLAlchemy that queries a PostgreSQL database to store and fetch chats and their messages.  

The API will crash without a PostgreSQL database server running, for instructions, see the [db' Readme](../db/README.md). 

# Running the server
There are several ways to run the API. We'll make it available at http://localhost:8001. 

## Python server on localhost
By default, the API expects the database server at localhost:5432 with "myusername" and "mypassword". To run the Python server manually, first create a virtual environment and install the packages in `requirements.txt`. 

To start the API as single Uvicorn dev server with default (local) host ip address on host machine's port 8001:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

Or as Gunicorn process manager with 4 uvicorn worker processes. Available at  http://localhost:8001.
```bash
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

## Docker container with private network
Docker containers are completely isolated they have their own localhost. This means that if we run the API in a Docker container, it cannot reach the database server running on our computer's localhost: they both need to be on the same private network.

In this network the API can find the database server by the db's container name that we pass as environment variable, which gets resolved to its container's IP address using Docker DNS. We publish the container port 80 to our host machine's port 8001.
```bash
docker build -t db-api-image .
docker run -d --name db-api --network chat-net --publish 8001:80 --env POSTGRES_HOST=db --env POSTGRES_USER=myuser --env POSTGRES_PASSWORD=mypassword db-api-image
```

## Docker Compose
To run the API with Docker Compose, see [compose.yml](../compose.yml).