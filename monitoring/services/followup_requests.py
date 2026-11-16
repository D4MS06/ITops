"""Common follow-up lifecycle and optional notification reminders."""

from __future__ import annotations


FOLLOWUP_TRANSITIONS = {
    "pending": frozenset({"sent", "cancelled"}),
    "sent": frozenset({"partial", "done", "rejected"}),
    "partial": frozenset({"partial", "done", "rejected"}),
}
FOLLOWUP_REMINDER_FIELD = "followup_request"


def require_followup_transition(current: str, target: str) -> None:
    if target not in FOLLOWUP_TRANSITIONS.get(str(current or "").strip().lower(), ()):
        raise ValueError("Transition de suivi indisponible pour cette demande.")


def sync_followup_reminder(store, request: dict) -> None:
    """Schedule or cancel a reminder linked to one follow-up request."""
    module_code = str(request.get("module_code") or "").strip().lower()
    request_id = str(request.get("id") or "").strip()
    record_id = str(request.get("record_id") or request_id).strip()
    if not module_code or not request_id or not record_id:
        raise ValueError("Demande de suivi invalide.")
    key = {
        "source_service_code": module_code,
        "source_record_id": record_id,
        "trigger_field_key": FOLLOWUP_REMINDER_FIELD,
        "trigger_value": request_id,
    }
    due_at = str(request.get("reminder_due_at") or "").strip()
    status = str(request.get("status") or "").strip().lower()
    if status == "sent" and due_at:
        updater = getattr(store, "upsert_notification_task", None)
        if not callable(updater):
            raise RuntimeError("Moteur de rappels indisponible.")
        target = str(request.get("target_value") or "").strip()
        updater(
            **key,
            title=f"Vérifier la demande {target or request_id}"[:255],
            message=f"Vérifier la réponse et valider la demande {target or request_id} dans le suivi.",
            due_at=due_at,
        )
    elif status in {"done", "rejected", "cancelled"} or not due_at:
        canceller = getattr(store, "cancel_notification_tasks_for_source", None)
        if callable(canceller):
            canceller(**key)
