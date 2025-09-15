## Overview

A FastAPI server for enabling API access to a live Ollama model..

## Architecture & Features

- Docker & Ollama integration with baked-in models  
- Two API versions:
  - **v1**: Simple prompt-to-text  
  - **v2**: Advanced chat (history, system prompts, tool calling, image recognition)  
- Makefile for environment setup, builds, and workflows  
- Built-in testing, linting, and formatting

## API References

For detailed API specs, see:
- [v2 Chat Completions](src/api/v2/README.md)
- [v1 Simple Proxy](src/api/v1/README.md)

## SDKs

Client libraries for Python:
- [v2 (chat & tools)](sdk/olm_api_client/v2/README.md)
- [v1 (prompt only)](sdk/olm_api_client/v1/README.md)

