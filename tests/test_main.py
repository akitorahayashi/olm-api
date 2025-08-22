from unittest.mock import MagicMock

import ollama
import pytest
from fastapi.testclient import TestClient

from src.main import app, get_ollama_client

# --- Mock Setup ---

# 各テストでモックの振る舞いを個別に設定するため、
# グローバルなモックインスタンスの振る舞い設定は削除します。
mock_ollama_client = MagicMock()


def override_get_ollama_client():
    """
    テスト用のOllamaクライアントモックを返す依存関係オーバーライド関数。
    """
    return mock_ollama_client


# アプリケーションの依存関係をオーバーライド
app.dependency_overrides[get_ollama_client] = override_get_ollama_client


# --- Fixtures ---


@pytest.fixture(autouse=True)
def override_settings(monkeypatch):
    """
    テスト実行中に環境変数を設定します。
    """
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://test-ollama:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")


@pytest.fixture
def client():
    """
    FastAPI TestClient を生成するフィクスチャ。
    """
    # 各テストの前にモックの状態をリセット
    mock_ollama_client.reset_mock()
    return TestClient(app)


# --- Test Cases ---


def test_generate_success(client):
    """
    /generate エンドポイントが正常に動作する場合のテストケース（非ストリーミング）。
    """
    # このテストケース用のモックの戻り値を設定
    mock_chat_response = {"message": {"content": "モックされた応答です"}}
    mock_ollama_client.chat.return_value = mock_chat_response

    # APIへリクエストを送信
    response = client.post("/generate", json={"prompt": "こんにちは", "stream": False})

    # レスポンスの検証
    assert response.status_code == 200
    assert response.json() == {"response": "モックされた応答です"}

    # モックが正しく呼び出されたか検証
    mock_ollama_client.chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "こんにちは"}],
        stream=False,
    )


def test_generate_stream_success(client):
    """
    /generate エンドポイントが正常に動作する場合のテストケース（ストリーミング）。
    """

    # ストリーミング用のモックジェネレータを設定
    def mock_stream_generator():
        yield {"message": {"content": "レスポンス"}}
        yield {"message": {"content": "1"}}
        yield {"message": {"content": "レスポンス"}}
        yield {"message": {"content": "2"}}

    mock_ollama_client.chat.return_value = mock_stream_generator()

    # APIへリクエストを送信
    response = client.post(
        "/generate", json={"prompt": "ストリーミングして", "stream": True}
    )

    # レスポンスの検証
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # ストリームコンテンツを結合して検証
    full_response = "".join(response.iter_text())
    assert full_response == "レスポンス1レスポンス2"

    # モックが正しく呼び出されたか検証
    mock_ollama_client.chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "ストリーミングして"}],
        stream=True,
    )


def test_generate_ollama_api_error(client):
    """
    Ollama APIがエラーを返した場合のテストケース。
    """
    # モックが例外を送出するように設定
    error_message = "Ollama server is not available"
    mock_ollama_client.chat.side_effect = ollama.ResponseError(
        error_message, status_code=503
    )

    # APIへリクエストを送信
    response = client.post(
        "/generate", json={"prompt": "エラーを起こして", "stream": False}
    )

    # レスポンスの検証
    assert response.status_code == 500
    assert response.json() == {"detail": f"Ollama API error: {error_message}"}

    # モックが正しく呼び出されたか検証
    mock_ollama_client.chat.assert_called_once()
