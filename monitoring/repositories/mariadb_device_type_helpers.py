from __future__ import annotations

from typing import Any


def normalize_type_code(raw_code: str) -> str:
    code = str(raw_code or "").strip().lower()
    return "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in code)


def clone_type_schema(conn: Any, source_type: str, target_type: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM device_type_fields WHERE type_code = %s", (target_type,))
        cursor.execute("DELETE FROM device_type_actions WHERE type_code = %s", (target_type,))

        cursor.execute(
            """
            SELECT field_key, label, field_kind, required, options, default_value, show_in_table, sort_order
            FROM device_type_fields
            WHERE type_code = %s
            ORDER BY sort_order, id
            """,
            (source_type,),
        )
        field_rows = cursor.fetchall()
        if field_rows:
            cursor.executemany(
                """
                INSERT INTO device_type_fields(
                    type_code, field_key, label, field_kind, required, options, default_value, show_in_table, sort_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        target_type,
                        str(field_key),
                        str(label),
                        str(field_kind),
                        int(required or 0),
                        str(options or ""),
                        str(default_value or ""),
                        int(show_in_table or 0),
                        int(sort_order or 0),
                    )
                    for field_key, label, field_kind, required, options, default_value, show_in_table, sort_order in field_rows
                ],
            )

        cursor.execute(
            """
            SELECT action_key, label, target_kind, target_value, os_scope, sort_order, is_default
            FROM device_type_actions
            WHERE type_code = %s
            ORDER BY sort_order, id
            """,
            (source_type,),
        )
        action_rows = cursor.fetchall()
        if action_rows:
            cursor.executemany(
                """
                INSERT INTO device_type_actions(
                    type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        target_type,
                        str(action_key),
                        str(label),
                        str(target_kind),
                        str(target_value or ""),
                        str(os_scope or ""),
                        int(sort_order or 0),
                        int(is_default or 0),
                    )
                    for action_key, label, target_kind, target_value, os_scope, sort_order, is_default in action_rows
                ],
            )
