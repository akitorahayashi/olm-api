# Use the official Ollama image as the base
FROM ollama/ollama

# Argument to specify the model to be pulled during the build
ARG BUILT_IN_OLLAMA_MODEL

# Set the host to 0.0.0.0 to allow connections from other containers
ENV OLLAMA_HOST=0.0.0.0

# Install curl, which is used for healthcheck polling to ensure the server is ready.
# We switch to the root user to install packages.
USER root
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Pull the specified model into the image.
# This makes the model part of the immutable image.
# We start the server in the background, wait for it to become responsive, and then pull the model.
RUN ollama serve > /dev/null 2>&1 & \
    while ! curl -s -f http://127.0.0.1:11434 > /dev/null; do \
    echo "Waiting for ollama server to start..."; \
    sleep 1; \
    done; \
    ollama pull ${BUILT_IN_OLLAMA_MODEL}
