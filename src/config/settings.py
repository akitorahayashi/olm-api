import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_env_file():
    """
    実行環境に応じて.envファイルを動的に選択する。

    APP_ENV環境変数が'prod'なら'.env.prod'を、'test'なら'.env.test'を、
    それ以外（未設定含む）の場合は'.env.dev'を読み込みます。
    """
    env = os.getenv("APP_ENV", "dev")
    env_files = {
        "dev": ".env.dev",
        "prod": ".env.prod",
        "test": ".env.dev",  # test also uses dev settings for now
    }
    return env_files.get(env, ".env.dev")


class Settings(BaseSettings):
    """
    環境変数を管理するための設定クラス。

    このクラスは、アプリケーション全体で使用される設定値を環境変数から読み込みます。
    `get_env_file`関数によって、実行環境に応じた.envファイルが選択されます。
    """

    model_config = SettingsConfigDict(
        env_file=get_env_file(), env_file_encoding="utf-8"
    )

    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    DATABASE_URL: str
