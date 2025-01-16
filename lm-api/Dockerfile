# This dockerfile is for part 2 where we'll deploy the llama.cpp server to a docker container with the model file in
# the docker image rather than as a mounted volume.

FROM ghcr.io/ggerganov/llama.cpp:server

COPY models /models

# Run the inference API server with max 128 response tokens, flash attention, and 4096 context
CMD ["-m", "/models/qwen2.5-0.5b-instruct-q5_k_m.gguf", "--port", "80", "--host", "0.0.0.0", "-n", "128", "-fa", "-c", "1024"]