import json

from app.models.activity_log import ActivityLog


def log_activity(
    db,
    project_id,
    user_id,
    action,
    entity_type,
    entity_id,
    metadata=None,
    actor_type="USER",
    commit=False,
):

    activity = ActivityLog(
        project_id=project_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=json.dumps(metadata or {}),
        actor_type=actor_type,
    )

    db.add(activity)
    if commit:
        db.commit()
    return activity
