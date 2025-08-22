from fastapi import FastAPI
from ollama import Ollama
from pydantic import BaseModel

# LLM操作クラスを初期化
ollama_client = Ollama(model="Qwen-3:8B")

app = FastAPI(title="PVT-LLM-API", version="0.1")


class PromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 512


@app.post("/generate")
async def generate(req: PromptRequest):
    response = ollama_client.generate(req.prompt, max_tokens=req.max_tokens)
    return {"response": response.text}
