# Language model API
This directory does not contain any code but simply documents how to manually run the language model API as a Docker container. When running the full app, we use Docker Compose. 

I'm using the [llama.cpp inference engine](https://github.com/ggerganov/llama.cpp/blob/master) written in C/C++ that provides a [Docker API server image](https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md)  implementing the popular [OpenAI API specification](https://github.com/openai/openai-openapi?tab=readme-ov-file). It comes with a basic UI for experimenting. 

The language model itself is the quantized [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF) model from Alibaba Cloud.

## Running the server
The gguf model file should be in the `lm-api/models` directory. To make the language model API available at localhost:8000 and internally to containers on the same private network by its container name:
```bash
wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q5_k_m.gguf -P lm-api/models
docker run
  --name lm-api \
  --publish 8000:80 \
  --network chat-net \
  --volume $PROJECT_PATH/lm-api/models:/models \
  ghcr.io/ggerganov/llama.cpp:server \
    -m /models/qwen2.5-0_5b-instruct-q5_k_m.gguf --port 80 --host 0.0.0.0 -n 512 -fa
```
To test the server:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
-H "Content-Type: application/json" \
-d '{
	"messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "assistant", "content": "Hello, how can I assist you today?"},
    {"role": "user", "content": "Hi, what is an API?"}
	],
	"max_tokens": 10
	}'
```
## Why a Dockerfile?
We don't need a Dockerfile to run the LM-API locally since we simply mount the model directory. The Dockerfile copies the model file into the image and we use it when deploying to Azure to avoid uploading the model to some file storage and then mounting that to Azure Container Apps. 
