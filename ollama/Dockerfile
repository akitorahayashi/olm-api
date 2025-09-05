# Use the official Ollama image as the base
FROM ollama/ollama

# Argument to specify the model to be pulled during the build
ARG BUILT_IN_OLLAMA_MODEL

# Set the host to 0.0.0.0 to allow connections from other containers
ENV OLLAMA_HOST=0.0.0.0

# Install curl, which is used for healthcheck polling.
USER root
RUN apt-get clean && \
  apt-get update && \
  apt-get install -y curl && \
  rm -rf /var/lib/apt/lists/*

# Pull the specified model into the image.
RUN ollama serve > /dev/null 2>&1 & \
  while ! curl -s -f http://127.0.0.1:11434 > /dev/null; do \
  echo "Waiting for ollama server to start..."; \
  sleep 1; \
  done; \
  ollama pull ${BUILT_IN_OLLAMA_MODEL}

# Add a healthcheck to ensure the Ollama server is responsive
HEALTHCHECK --interval=10s --timeout=5s --start-period=300s --retries=30 \
  CMD curl -fsS http://127.0.0.1:11434 >/dev/null || exit 1
