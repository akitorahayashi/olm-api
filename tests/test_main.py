import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from src.main import app, get_ollama_client

# テスト用のOllamaクライアントのモックを設定
mock_chat_response = {"message": {"content": "モックされた応答です"}}
mock_ollama_client = MagicMock()
mock_ollama_client.chat.return_value = mock_chat_response

def override_get_ollama_client():
    """
    テスト用のOllamaクライアントモックを返す依存関係オーバーライド関数。
    """
    return mock_ollama_client

# アプリケーションの依存関係をオーバーライド
app.dependency_overrides[get_ollama_client] = override_get_ollama_client


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
    return TestClient(app)


def test_generate_success(client):
    """
    /generate エンドポイントが正常に動作する場合のテストケース。
    依存関係のオーバーライドにより、モッククライアントが使用されます。
    """
    # APIへリクエストを送信
    response = client.post("/generate", json={"prompt": "こんにちは", "stream": False})

    # レスポンスの検証
    assert response.status_code == 200
    assert response.json() == {"response": "モックされた応答です"}

    # モックが正しく呼び出されたか検証
    mock_ollama_client.chat.assert_called_once_with(
        model="test-model",
        messages=[{"role": "user", "content": "こんにちは"}],
        stream=False
    )

    # 各テスト後にモックの呼び出し履歴をリセット
    mock_ollama_client.chat.reset_mock()
