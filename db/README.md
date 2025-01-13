# PostgreSQL database server
This directory does not contain any code but simply documents how to manually run a PostgreSQL database server in a Docker container using the official postgres image.


## Running the database server
To make the database available at localhost:5432 on our local computer and at db:5432 for containers on the same private network:
```bash
docker network create --driver bridge chat-net
docker run --name db --network chat-net --publish 5432:5432 --env POSTGRES_USER=myuser --env POSTGRES_PASSWORD=mypassword postgres
```
