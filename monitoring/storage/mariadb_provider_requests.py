"""Persistence and atomic confirmation of provider requests."""

from __future__ import annotations

import datetime as dt
import json
import re
import uuid

from monitoring.services.custom_service_index import upsert_record_index
from monitoring.services.followup_requests import require_followup_transition
from monitoring.services.provider_requests import confirmed_mail_changes, rejected_mail_changes


_COLUMNS = ("id", "module_code", "record_id", "action_code", "target_value", "reminder_due_at", "recipient", "subject", "body", "expected_values_json", "original_values_json", "confirmed_values_json", "events_json", "requested_by", "resolved_by", "status", "resolution_note", "sent_at", "resolved_at", "created_at", "updated_at")
_SELECT = ", ".join(_COLUMNS)


def _row(row) -> dict | None:
    if not row:
        return None
    values = dict(row) if isinstance(row, dict) else dict(zip(_COLUMNS, row))
    for key in ("expected_values_json", "original_values_json", "confirmed_values_json", "events_json"):
        values[key.removesuffix("_json")] = json.loads(values.pop(key) or ("[]" if key == "events_json" else "{}"))
    return {key: str(value or "") if key not in {"expected_values", "original_values", "confirmed_values", "events"} else value for key, value in values.items()}


def _event(status: str, actor: str, note: str = "") -> dict[str, str]:
    return {"status": status, "actor": actor, "note": str(note or "")[:2000],
            "at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}


class ProviderRequestMixin:
    def _provider_request_record(self, record_id: str) -> dict | None:
        return next((row for row in self.list_custom_service_records(service_code="emails") if str(row.get("id") or "") == record_id), None)

    @staticmethod
    def _save_email_changes(cursor, *, record_id: str, current: dict, changes: dict[str, str], actor: str) -> None:
        updated = dict(current)
        for key, value in changes.items():
            old_value = str(updated.get(key) or "")
            updated[key] = value
            if old_value != str(value):
                cursor.execute("""INSERT INTO custom_service_record_history
                    (service_code, record_id, field_key, old_value, new_value, changed_at, changed_by, change_source)
                    VALUES ('emails', %s, %s, %s, %s, UTC_TIMESTAMP(), %s, 'provider_request')""",
                    (record_id, key, old_value, value, actor))
        if changes:
            cursor.execute("UPDATE custom_service_records SET payload_json = %s, updated_at = UTC_TIMESTAMP() WHERE id = %s",
                           (json.dumps(updated, ensure_ascii=False), record_id))

    def list_provider_requests(self, *, module_code: str = "", record_id: str = "", limit: int = 500) -> list[dict]:
        self._ensure_database()
        conditions = []
        params: list[object] = []
        if module_code:
            conditions.append("module_code = %s")
            params.append(str(module_code).strip().lower())
        if record_id:
            conditions.append("record_id = %s")
            params.append(str(record_id).strip())
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {_SELECT} FROM provider_requests{where} ORDER BY created_at DESC LIMIT %s", (*params, max(1, min(1000, int(limit)))))
                return [_row(item) for item in cursor.fetchall() or []]

    def get_provider_request(self, *, request_id: str) -> dict | None:
        self._ensure_database()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {_SELECT} FROM provider_requests WHERE id = %s", (str(request_id).strip(),))
                return _row(cursor.fetchone())

    def create_provider_request(self, *, module_code: str, record_id: str, action_code: str, target_value: str, reminder_due_at: str = "", recipient: str, subject: str, body: str, expected_values: dict, confirmed_values: dict, requested_by: str) -> dict:
        request_id = uuid.uuid4().hex
        self._ensure_database()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""INSERT INTO provider_requests
                    (id, module_code, record_id, action_code, target_value, reminder_due_at, recipient, subject, body,
                     expected_values_json, original_values_json, confirmed_values_json, events_json, requested_by, status, resolution_note)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', '')""",
                    (request_id, module_code, record_id, action_code, target_value, str(reminder_due_at or "").strip() or None, recipient, subject, body,
                     json.dumps(expected_values, ensure_ascii=False), json.dumps(expected_values, ensure_ascii=False), json.dumps(confirmed_values, ensure_ascii=False),
                     json.dumps([_event("pending", requested_by)], ensure_ascii=False), requested_by))
                conn.commit()
        return self.get_provider_request(request_id=request_id)

    def mark_provider_request_sent(self, *, request_id: str, sent_by: str = "") -> dict:
        """Record delivery and move a deletion request to the existing pending status."""
        self._ensure_database()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {_SELECT} FROM provider_requests WHERE id = %s FOR UPDATE", (request_id,))
                request = _row(cursor.fetchone())
                if not request:
                    raise ValueError("Demande introuvable.")
                require_followup_transition(request["status"], "sent")
                if request["module_code"] == "emails" and request["action_code"] == "delete":
                    cursor.execute("SELECT payload_json FROM custom_service_records WHERE id = %s AND service_code = 'emails' AND trashed_at IS NULL FOR UPDATE", (request["record_id"],))
                    record_row = cursor.fetchone()
                    if not record_row:
                        raise ValueError("Compte mail introuvable.")
                    values = json.loads(record_row[0] or "{}")
                    old_status = str(values.get("status") or "")
                    if old_status != str(request["expected_values"].get("status") or ""):
                        raise ValueError("Le statut du compte a changé depuis la demande.")
                    self._save_email_changes(cursor, record_id=request["record_id"], current=values,
                                             changes={"status": "A supprimer"}, actor=request["requested_by"])
                    request["expected_values"]["status"] = "A supprimer"
                    cursor.execute("UPDATE provider_requests SET expected_values_json = %s WHERE id = %s", (json.dumps(request["expected_values"], ensure_ascii=False), request_id))
                events = [*request["events"], _event("sent", sent_by or request["requested_by"])]
                cursor.execute("UPDATE provider_requests SET status = 'sent', sent_at = UTC_TIMESTAMP(), events_json = %s WHERE id = %s", (json.dumps(events, ensure_ascii=False), request_id))
                conn.commit()
        if request["module_code"] == "emails" and request["action_code"] == "delete":
            record = self._provider_request_record(request["record_id"])
            service = self.get_custom_service(code="emails")
            if record and service:
                upsert_record_index(manager=self, service=service, record=record)
        return self.get_provider_request(request_id=request_id)

    def cancel_pending_provider_request(self, *, request_id: str, resolved_by: str) -> dict:
        self._ensure_database()
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {_SELECT} FROM provider_requests WHERE id = %s FOR UPDATE", (request_id,))
                request = _row(cursor.fetchone())
                if not request:
                    raise ValueError("Demande introuvable.")
                require_followup_transition(request["status"], "cancelled")
                events = [*request["events"], _event("cancelled", resolved_by)]
                cursor.execute("""UPDATE provider_requests SET status = 'cancelled', resolved_by = %s,
                    resolved_at = UTC_TIMESTAMP(), events_json = %s WHERE id = %s""", (resolved_by, json.dumps(events, ensure_ascii=False), request_id))
                conn.commit()
        return self.get_provider_request(request_id=request_id)

    def resolve_provider_request(self, *, request_id: str, resolution: str, resolved_by: str, note: str = "", accept_current: bool = False) -> dict:
        if resolution not in {"done", "partial", "rejected"}:
            raise ValueError("Décision invalide.")
        self._ensure_database()
        changed_record_id = ""
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT {_SELECT} FROM provider_requests WHERE id = %s FOR UPDATE", (request_id,))
                request = _row(cursor.fetchone())
                if not request:
                    raise ValueError("Demande introuvable.")
                require_followup_transition(request["status"], resolution)
                if resolution == "done":
                    if request["module_code"] != "emails":
                        raise ValueError("Module sans adaptateur de validation.")
                    changes = request["confirmed_values"]
                    if request["action_code"] in {"create", "add_alias"}:
                        cursor.execute("SELECT id, payload_json FROM custom_service_records WHERE service_code = 'emails' AND trashed_at IS NULL FOR UPDATE")
                        for existing_id, raw_values in cursor.fetchall() or []:
                            if request["action_code"] == "add_alias" and str(existing_id) == request["record_id"]:
                                continue
                            existing_values = json.loads(raw_values or "{}")
                            occupied = {str(existing_values.get("address") or "").strip().lower()}
                            occupied.update(part.strip().lower() for part in re.split(r"[,;\n]+", str(existing_values.get("alias") or "")) if part.strip())
                            if request["target_value"].lower() in occupied:
                                raise ValueError("Cette adresse ou cet alias existe déjà dans Emails.")
                    if request["action_code"] == "create":
                        changed_record_id = uuid.uuid4().hex
                        cursor.execute("""INSERT INTO custom_service_records
                            (id, service_code, payload_json, sync_source_kind, sync_target_kind, sync_external_id, sync_status, trashed_at, trash_reason, created_at, updated_at)
                            VALUES (%s, 'emails', %s, '', '', '', 'active', NULL, '', UTC_TIMESTAMP(), UTC_TIMESTAMP())""",
                            (changed_record_id, json.dumps(changes, ensure_ascii=False)))
                        cursor.executemany("""INSERT INTO custom_service_record_history
                            (service_code, record_id, field_key, old_value, new_value, changed_at, changed_by, change_source)
                            VALUES ('emails', %s, %s, '', %s, UTC_TIMESTAMP(), %s, 'provider_request')""",
                            [(changed_record_id, key, str(value), resolved_by) for key, value in changes.items()])
                        cursor.execute("UPDATE provider_requests SET record_id = %s WHERE id = %s", (changed_record_id, request_id))
                    elif changes:
                        changed_record_id = request["record_id"]
                        cursor.execute("SELECT payload_json FROM custom_service_records WHERE id = %s AND service_code = 'emails' AND trashed_at IS NULL FOR UPDATE", (changed_record_id,))
                        record_row = cursor.fetchone()
                        if not record_row:
                            raise ValueError("Compte mail introuvable.")
                        values = json.loads(record_row[0] or "{}")
                        changes = confirmed_mail_changes(
                            action=request["action_code"], target_value=request["target_value"],
                            expected=request["expected_values"], confirmed=changes,
                            current=values, accept_current=accept_current,
                        )
                        self._save_email_changes(cursor, record_id=changed_record_id, current=values,
                                                 changes=changes, actor=resolved_by)
                elif resolution == "rejected" and request["module_code"] == "emails" and request["action_code"] == "delete":
                    changed_record_id = request["record_id"]
                    cursor.execute("SELECT payload_json FROM custom_service_records WHERE id = %s AND service_code = 'emails' AND trashed_at IS NULL FOR UPDATE", (changed_record_id,))
                    record_row = cursor.fetchone()
                    if not record_row:
                        raise ValueError("Compte mail introuvable.")
                    values = json.loads(record_row[0] or "{}")
                    changes = rejected_mail_changes(
                        action=request["action_code"], current=values,
                        expected=request["expected_values"], original=request["original_values"],
                    )
                    self._save_email_changes(cursor, record_id=changed_record_id, current=values,
                                             changes=changes, actor=resolved_by)
                events = [*request["events"], _event(resolution, resolved_by, note)]
                cursor.execute("""UPDATE provider_requests SET status = %s, resolved_by = %s,
                    resolution_note = CASE WHEN %s <> '' THEN %s ELSE resolution_note END,
                    resolved_at = CASE WHEN %s = 'partial' THEN NULL ELSE UTC_TIMESTAMP() END,
                    events_json = %s WHERE id = %s""",
                    (resolution, resolved_by, str(note or "")[:2000], str(note or "")[:2000], resolution,
                     json.dumps(events, ensure_ascii=False), request_id))
                conn.commit()
        if changed_record_id:
            record = self._provider_request_record(changed_record_id)
            service = self.get_custom_service(code="emails")
            if record and service:
                upsert_record_index(manager=self, service=service, record=record)
        return self.get_provider_request(request_id=request_id)
