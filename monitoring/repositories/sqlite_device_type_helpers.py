from __future__ import annotations

import sqlite3


def normalize_type_code(raw_code: str) -> str:
    code = str(raw_code or "").strip().lower()
    return "".join(ch if (ch.isalnum() or ch in {"_", "-"}) else "_" for ch in code)


def clone_type_schema(conn: sqlite3.Connection, source_type: str, target_type: str) -> None:
    conn.execute("DELETE FROM device_type_fields WHERE type_code = ?", (target_type,))
    conn.execute("DELETE FROM device_type_actions WHERE type_code = ?", (target_type,))

    field_rows = conn.execute(
        """
        SELECT field_key, label, field_kind, required, options, default_value, sort_order
        FROM device_type_fields
        WHERE type_code = ?
        ORDER BY sort_order, id
        """,
        (source_type,),
    ).fetchall()
    conn.executemany(
        """
        INSERT INTO device_type_fields(
            type_code, field_key, label, field_kind, required, options, default_value, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                int(sort_order or 0),
            )
            for field_key, label, field_kind, required, options, default_value, sort_order in field_rows
        ],
    )

    action_rows = conn.execute(
        """
        SELECT action_key, label, target_kind, target_value, os_scope, sort_order, is_default
        FROM device_type_actions
        WHERE type_code = ?
        ORDER BY sort_order, id
        """,
        (source_type,),
    ).fetchall()
    conn.executemany(
        """
        INSERT INTO device_type_actions(
            type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
