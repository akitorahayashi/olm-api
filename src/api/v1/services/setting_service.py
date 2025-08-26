from sqlalchemy.exc import IntegrityError
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
    Sets the active model name in the database using a last-writer-wins strategy.

    This function performs an "upsert" operation. It first attempts to update
    the existing setting. If the setting does not exist, it attempts to insert it.
    If a race condition occurs where another process inserts the setting
    concurrently, this function catches the `IntegrityError`, rolls back, and
    then performs an `UPDATE` to ensure the caller's intended value is stored.

    Args:
        db (Session): The database session.
        model_name (str): The name of the model to set as active.
    """
    # First, try to update an existing record.
    updated = (
        db.query(Setting)
        .filter(Setting.key == ACTIVE_MODEL_KEY)
        .update({"value": model_name}, synchronize_session=False)
    )

    if updated:
        db.commit()
        return

    # If no record was updated, it might not exist. Try to insert.
    try:
        setting = Setting(key=ACTIVE_MODEL_KEY, value=model_name)
        db.add(setting)
        db.commit()
    except IntegrityError:
        # A concurrent transaction created the record. Rollback the failed
        # insert and then update the record to ensure last-writer-wins.
        db.rollback()
        db.query(Setting).filter(Setting.key == ACTIVE_MODEL_KEY).update(
            {"value": model_name}, synchronize_session=False
        )
        db.commit()
