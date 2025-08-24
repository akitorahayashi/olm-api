from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    環境変数を管理するための設定クラス。

    このクラスは、アプリケーション全体で使用される設定値を環境変数から読み込みます。
    Docker Composeがプロジェクトルートの.envファイル（シンボリックリンク）を
    自動的に読み込むため、ファイルパスを明示的に指定する必要はありません。
    """

    OLLAMA_MODEL: str
    DATABASE_URL: str
