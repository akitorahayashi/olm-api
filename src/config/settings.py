from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    環境変数を管理するための設定クラス。

    このクラスは、アプリケーション全体で使用される設定値を環境変数から読み込みます。
    ローカル開発時には、.envファイルから設定を読み込むことができます。
    """

    # .envファイルを読み込むための設定
    # model_config に SettingsConfigDict を設定することで、.env ファイルの場所を指定します。
    # これにより、ローカル開発環境で環境変数を簡単に管理できます。
    # CI/CD環境など、.env ファイルが存在しない場合は、システムの環境変数が直接使用されます。
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    OLLAMA_BASE_URL: str
    OLLAMA_MODEL: str
    DATABASE_URL: str
