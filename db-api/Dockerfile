# Images are built incrementally layer per layer, based on the instructions starting from the top of the Dockerfile.
# An internal cache stores layers that can be reused when rebuilding an image. Therefore, copying and installing the
# requirements before the copying the code allows docker to retrieve those layer from the cache without rebuilding them.
# Code changes more frequently (and copying it is cheap) so it's among the last steps and requires rebuilding that layer.

# Use the official Python image from the Docker Hub
FROM python:3.12

# Set the working directory within the container
WORKDIR /code

# Copy the requirements file into to the working directory of the container
COPY requirements.txt /code/requirements.txt

# Install the requirements by running a pip command
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the fastapi code into the container
COPY app /code/app

# Run a uvicorn web server, exposing the app on port 80, listening on all interfaces (0.0.0.0, i.e., from any ip),
# and enabling nginx proxy
CMD ["uvicorn", "app.main:app", "--port", "80", "--proxy-headers", "--host", "0.0.0.0", "--log-level", "info"]
