# Nginx reverse proxy
This directory contains the configuration file for an Nginx reverse proxy that routes requests to services hidden behind a private network.

## Running the server
To make the reverse proxy available in the private network and at our localhost:
 ```bash
 docker network create --driver bridge chat-net
 docker run --network chat-net --publish 80:80 --volume $PROJECT_PATH/nginx.conf:/etc/nginx/nginx.conf -d nginx
 ```