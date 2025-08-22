from functools import lru_cache
from fastapi import FastAPI, Depends
from pydantic import BaseModel
import ollama
from src.settings import Settings

app = FastAPI(
    title="PVT-LLM-API",
    version="0.1.0",
    description="A private LLM API server using FastAPI and Ollama.",
)


# --- Dependency Injection ---

@lru_cache
def get_settings() -> Settings:
    """
    設定オブジェクトを生成する依存関係関数。
    @lru_cacheデコレータにより、設定は初回呼び出し時に一度だけ読み込まれます。
    """
    return Settings()


def get_ollama_client(settings: Settings = Depends(get_settings)) -> ollama.Client:
    """
    Ollamaクライアントのインスタンスを生成する依存関係関数。
    設定オブジェクトも依存性注入によって提供されます。
    """
    yield ollama.Client(host=settings.OLLAMA_BASE_URL)


class GenerateRequest(BaseModel):
    prompt: str
    stream: bool = False


class GenerateResponse(BaseModel):
    response: str


@app.post("/generate", response_model=GenerateResponse)
async def generate(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
    ollama_client: ollama.Client = Depends(get_ollama_client),
):
    """
    指定されたプロンプトに基づいてテキストを生成します。
    設定とOllamaクライアントは依存性注入によって提供されます。
    """
    chat_response = ollama_client.chat(
        model=settings.OLLAMA_MODEL,
        messages=[{"role": "user", "content": request.prompt}],
        stream=request.stream,
    )
    response_content = chat_response["message"]["content"]
    return GenerateResponse(response=response_content)
