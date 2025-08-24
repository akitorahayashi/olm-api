# Base image for Ollama
FROM ollama/ollama

# Argument for the model name, which will be passed during the build process
ARG OLLAMA_MODEL

# Set the host to allow access from other containers
ENV OLLAMA_HOST=0.0.0.0

# Download the specified model into the image during the build
# This ensures the model is part of the immutable image
RUN ollama pull ${OLLAMA_MODEL}

# The default command to run when the container starts
CMD ["ollama", "serve"]
