from sqlalchemy.orm import Session

from src.db.models.setting import Setting

ACTIVE_MODEL_KEY = "active_model_name"


def get_active_model(db: Session) -> str | None:
    """
    Retrieves the active model name from the database.

    Args:
        db (Session): The database session.

    Returns:
        str | None: The name of the active model, or None if not set.
    """
    setting = db.query(Setting).filter(Setting.key == ACTIVE_MODEL_KEY).first()
    return setting.value if setting else None


def set_active_model(db: Session, model_name: str):
    """
    Sets the active model name in the database.

    This function performs an "upsert" operation. If the setting for the
    active model already exists, it updates the value. If it does not exist,
    it creates a new entry.

    Args:
        db (Session): The database session.
        model_name (str): The name of the model to set as active.
    """
    setting = db.query(Setting).filter(Setting.key == ACTIVE_MODEL_KEY).first()
    if setting:
        setting.value = model_name
    else:
        setting = Setting(key=ACTIVE_MODEL_KEY, value=model_name)
        db.add(setting)
    db.commit()
