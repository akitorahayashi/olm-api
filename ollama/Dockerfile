# Use the official Ollama image as the base
FROM ollama/ollama

# Argument to specify the models to be pulled during the build (comma-separated)
ARG BUILT_IN_OLLAMA_MODELS="qwen3:0.6b"

# Set the host to 0.0.0.0 to allow connections from other containers
ENV OLLAMA_HOST=0.0.0.0

# Install curl, which is used for healthcheck polling.
USER root
RUN apt-get clean && \
  for i in 1 2 3; do \
  apt-get update && apt-get install -y curl && break; \
  echo "apt-get failed, retrying in 5 seconds..."; \
  sleep 5; \
  done && \
  rm -rf /var/lib/apt/lists/*

# Pull the specified models into the image.
RUN set -eux; \
  ollama serve > /dev/null 2>&1 & \
  t=0; \
  until curl -sSf --max-time 2 http://127.0.0.1:11434 > /dev/null; do \
    if [ "$t" -ge 300 ]; then echo "Timeout waiting for ollama server"; exit 1; fi; \
    echo "Waiting for ollama server to start..."; \
    sleep 1; \
    t=$((t+1)); \
  done; \
  \
  # Pull each model from comma-separated list \
  echo "Models to pull: ${BUILT_IN_OLLAMA_MODELS}"; \
  echo "${BUILT_IN_OLLAMA_MODELS}" | tr ',' '\n' | while IFS= read -r model; do \
    model=$(echo "$model" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'); \
    if [ -n "$model" ]; then \
      echo "Pulling model: $model"; \
      if ! ollama pull "$model"; then \
        echo "ERROR: Failed to pull model: $model" >&2; \
        exit 1; \
      fi; \
    fi; \
  done

# Add a healthcheck to ensure the Ollama server is responsive
HEALTHCHECK --interval=10s --timeout=5s --start-period=300s --retries=30 \
  CMD curl -fsS http://127.0.0.1:11434 >/dev/null || exit 1
