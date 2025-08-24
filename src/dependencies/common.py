from functools import lru_cache

import ollama
from fastapi import Depends

from src.config.settings import Settings


@lru_cache
def get_settings() -> Settings:
    """
    Dependency function to create the settings object.
    Caches the settings object for performance.
    """
    return Settings()


def get_ollama_client() -> ollama.Client:
    """
    Dependency function to create an instance of the Ollama client.
    """
    # Using 'yield' makes this a generator-based dependency,
    # which is good practice for resources that might need cleanup.
    yield ollama.Client(host="http://ollama:11434")
