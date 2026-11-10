"""
Permanent creator identity.

`creator_name` is a plain String column written ONCE, when a record is inserted, from the
creator's full name at that moment. It is deliberately NOT a join to `users`: renaming the user,
changing their role, moving them, or deactivating / deleting the account never changes who is
recorded as having created the record. The value is also protected against later updates.
"""
from sqlalchemy import event, inspect, select

CREATOR_NAME_MAX = 200


def register(model) -> None:
    """Hook `model` (needs `created_by_user_id` and `creator_name` columns)."""

    @event.listens_for(model, "before_insert")
    def _snapshot_on_insert(mapper, connection, target):  # noqa: ANN001
        if getattr(target, "creator_name", None) or not getattr(target, "created_by_user_id", None):
            return
        from app.core.users.models import User  # local: avoids an import cycle at module load

        name = connection.execute(select(User.full_name).where(User.id == target.created_by_user_id)).scalar()
        if name:
            target.creator_name = str(name)[:CREATOR_NAME_MAX]

    @event.listens_for(model, "before_update")
    def _freeze_on_update(mapper, connection, target):  # noqa: ANN001
        hist = inspect(target).attrs.creator_name.history
        if hist.has_changes() and hist.deleted and hist.deleted[0]:
            target.creator_name = hist.deleted[0]  # never rewrite who originally created the record


def display_name(record) -> str | None:
    """The stored name; falls back to the live account only for rows created before the snapshot."""
    stored = getattr(record, "creator_name", None)
    if stored:
        return stored
    live = getattr(record, "created_by", None)
    return live.full_name if live is not None else None
