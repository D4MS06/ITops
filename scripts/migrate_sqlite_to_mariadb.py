from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

from monitoring.storage.mariadb_manager import MariaDBFileManager


def default_sqlite_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(local_app_data) / "NetworkMonitoringProject" / "data" / "devices.db"


def sqlite_rows(conn: sqlite3.Connection, query: str) -> list[tuple]:
    return conn.execute(query).fetchall()


def migrate(sqlite_path: Path) -> None:
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite introuvable: {sqlite_path}")

    mgr = MariaDBFileManager()
    mgr._ensure_database()

    with sqlite3.connect(str(sqlite_path)) as sqlite_conn:
        sqlite_conn.row_factory = None
        devices = sqlite_rows(
            sqlite_conn,
            """
            SELECT id, dtype, name, ip, description, notify,
                   id_teamviewer, subtype, action_double_click, web_url, ssh_user,
                   COALESCE(custom_data, '')
            FROM devices
            """,
        )
        device_types = sqlite_rows(
            sqlite_conn,
            """
            SELECT code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
            FROM device_types
            """,
        )
        device_type_fields = sqlite_rows(
            sqlite_conn,
            """
            SELECT type_code, field_key, label, field_kind, required, options, default_value, sort_order
            FROM device_type_fields
            """,
        )
        device_type_actions = sqlite_rows(
            sqlite_conn,
            """
            SELECT type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
            FROM device_type_actions
            """,
        )
        status_logs = sqlite_rows(
            sqlite_conn,
            """
            SELECT created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details
            FROM status_logs
            """,
        )
        config_versions = sqlite_rows(
            sqlite_conn,
            """
            SELECT file_path, device_type_label, device_name, filename, detail, created_at, updated_at
            FROM config_file_versions
            """,
        )
        auth_sessions = sqlite_rows(
            sqlite_conn,
            """
            SELECT token, subject, created_at, expires_at
            FROM auth_sessions
            """,
        )

    with mgr._connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            cursor.execute("DELETE FROM auth_sessions")
            cursor.execute("DELETE FROM status_logs")
            cursor.execute("DELETE FROM config_file_versions")
            cursor.execute("DELETE FROM device_type_actions")
            cursor.execute("DELETE FROM device_type_fields")
            cursor.execute("DELETE FROM devices")
            cursor.execute("DELETE FROM device_types")

            if device_types:
                cursor.executemany(
                    """
                    INSERT INTO device_types(
                        code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    device_types,
                )
            if device_type_fields:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    device_type_fields,
                )
            if device_type_actions:
                cursor.executemany(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    device_type_actions,
                )
            if devices:
                cursor.executemany(
                    """
                    INSERT INTO devices(
                        id, dtype, name, ip, description, notify,
                        id_teamviewer, subtype, action_double_click, web_url, ssh_user, custom_data
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    devices,
                )
            if status_logs:
                cursor.executemany(
                    """
                    INSERT INTO status_logs(
                        created_at, dtype, device_id, device_name, old_status, new_status, event_kind, details
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    status_logs,
                )
            if config_versions:
                cursor.executemany(
                    """
                    INSERT INTO config_file_versions(
                        file_path, device_type_label, device_name, filename, detail, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    config_versions,
                )
            if auth_sessions:
                cursor.executemany(
                    """
                    INSERT INTO auth_sessions(token, subject, created_at, expires_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    auth_sessions,
                )
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        conn.commit()

    print(f"Migration terminee depuis {sqlite_path}")
    print(f"Types: {len(device_types)} | Devices: {len(devices)} | Logs: {len(status_logs)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migre les donnees SQLite vers MariaDB.")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=default_sqlite_path(),
        help="Chemin vers le fichier SQLite source (devices.db).",
    )
    args = parser.parse_args()
    migrate(args.sqlite_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
