from functools import lru_cache

import ollama
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

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
    """
    return Settings()


def get_ollama_client(settings: Settings = Depends(get_settings)) -> ollama.Client:
    """
    Ollamaクライアントのインスタンスを生成する依存関係関数。
    """
    yield ollama.Client(host=settings.OLLAMA_BASE_URL)


# --- API Models ---


class GenerateRequest(BaseModel):
    prompt: str
    stream: bool = False


class GenerateResponse(BaseModel):
    response: str


# --- Endpoint ---


async def stream_generator(response_stream):
    """
    Ollamaからのストリーミング応答を処理し、クライアントに送信する非同期ジェネレータ。
    """
    for chunk in response_stream:
        if chunk["message"]["content"]:
            yield chunk["message"]["content"]


@app.post("/generate")
async def generate(
    request: GenerateRequest,
    settings: Settings = Depends(get_settings),
    ollama_client: ollama.Client = Depends(get_ollama_client),
):
    """
    指定されたプロンプトに基づいてテキストを生成します。
    - stream=False: テキスト全体をJSONで返します。
    - stream=True: テキストをチャンクでストリーミングします。
    Ollama APIからのエラーは捕捉され、500エラーとしてクライアントに返されます。
    """
    try:
        chat_response = ollama_client.chat(
            model=settings.OLLAMA_MODEL,
            messages=[{"role": "user", "content": request.prompt}],
            stream=request.stream,
        )

        if request.stream:
            # ストリーミング応答を返す
            return StreamingResponse(
                stream_generator(chat_response),
                media_type="text/event-stream",
            )
        else:
            # 完全な応答を一度に返す
            response_content = chat_response["message"]["content"]
            return GenerateResponse(response=response_content)

    except ollama.ResponseError as e:
        # Ollama APIからのエラーを捕捉
        # e.args[0] にエラーメッセージの本文が含まれていることを期待
        error_detail = e.args[0] if e.args else str(e)
        raise HTTPException(
            status_code=500,
            detail=f"Ollama API error: {error_detail}",
        )
    except Exception as e:
        # その他の予期せぬエラー
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )
