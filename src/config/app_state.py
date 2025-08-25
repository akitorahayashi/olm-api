class AppState:
    """
    アプリケーション全体の状態を管理するためのシングルトンクラス。

    現在アクティブな生成モデルの名前など、リクエストをまたいで共有される
    状態を保持します。
    """

    def __init__(self):
        self._current_model: str | None = None

    def get_current_model(self) -> str:
        """
        現在設定されている生成モデルの名前を取得します。

        Returns:
            str: モデル名。設定されていない場合はValueErrorを送出します。

        Raises:
            ValueError: モデルがまだ設定されていない場合に発生します。
        """
        if self._current_model is None:
            raise ValueError("The generation model has not been initialized.")
        return self._current_model

    def set_current_model(self, model_name: str):
        """
        生成モデルの名前を設定します。

        Args:
            model_name (str): 新しく設定するモデルの名前。
        """
        self._current_model = model_name


# シングルトンインスタンスを作成
app_state = AppState()
