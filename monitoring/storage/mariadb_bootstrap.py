from __future__ import annotations

import datetime as dt
import json
from hashlib import pbkdf2_hmac
from typing import List

from monitoring.storage.json_manager import JSONFileManager
from monitoring.utils.logger import log_with_timestamp


class MariaDBBootstrapper:
    @staticmethod
    def ensure_database(manager) -> None:
        manager._ensure_database_exists()
        with manager._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET SESSION sql_mode = ''")
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS devices (
                        id VARCHAR(191) PRIMARY KEY,
                        dtype VARCHAR(64) NOT NULL,
                        name VARCHAR(191) NOT NULL,
                        ip VARCHAR(191) NOT NULL,
                        description TEXT NOT NULL,
                        notify TINYINT(1) NOT NULL DEFAULT 1,
                        id_teamviewer VARCHAR(191) NOT NULL DEFAULT '',
                        subtype VARCHAR(191) NOT NULL DEFAULT '',
                        action_double_click VARCHAR(191) NOT NULL DEFAULT '',
                        web_url TEXT NOT NULL,
                        ssh_user VARCHAR(191) NOT NULL DEFAULT '',
                        device_login VARCHAR(191) NOT NULL DEFAULT '',
                        device_password VARCHAR(1024) NOT NULL DEFAULT '',
                        custom_data LONGTEXT NOT NULL,
                        KEY idx_devices_dtype_ip (dtype, ip),
                        KEY idx_devices_dtype_name (dtype, name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_types (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        icon VARCHAR(191) NOT NULL DEFAULT '',
                        monitoring_enabled TINYINT(1) NOT NULL DEFAULT 1,
                        config_backups_enabled TINYINT(1) DEFAULT NULL,
                        is_system TINYINT(1) NOT NULL DEFAULT 0,
                        sort_order INT NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_type_fields (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        type_code VARCHAR(64) NOT NULL,
                        field_key VARCHAR(191) NOT NULL,
                        label VARCHAR(191) NOT NULL,
                        field_kind VARCHAR(64) NOT NULL,
                        required TINYINT(1) NOT NULL DEFAULT 0,
                        options TEXT NOT NULL,
                        default_value TEXT NOT NULL,
                        show_in_table TINYINT(1) NOT NULL DEFAULT 0,
                        sort_order INT NOT NULL DEFAULT 0,
                        UNIQUE KEY uq_type_field (type_code, field_key),
                        CONSTRAINT fk_type_fields_code FOREIGN KEY (type_code)
                            REFERENCES device_types(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS device_type_actions (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        type_code VARCHAR(64) NOT NULL,
                        action_key VARCHAR(191) NOT NULL,
                        label VARCHAR(191) NOT NULL,
                        target_kind VARCHAR(64) NOT NULL DEFAULT 'builtin',
                        target_value TEXT NOT NULL,
                        os_scope TEXT NOT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        is_default TINYINT(1) NOT NULL DEFAULT 0,
                        UNIQUE KEY uq_type_action (type_code, action_key),
                        CONSTRAINT fk_type_actions_code FOREIGN KEY (type_code)
                            REFERENCES device_types(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS status_logs (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        created_at DATETIME NOT NULL,
                        dtype VARCHAR(64) NOT NULL,
                        device_id VARCHAR(191) NOT NULL,
                        device_name VARCHAR(191) NOT NULL,
                        old_status VARCHAR(64) NOT NULL,
                        new_status VARCHAR(64) NOT NULL,
                        event_kind VARCHAR(64) NOT NULL DEFAULT 'status_change',
                        details TEXT NOT NULL,
                        KEY idx_status_logs_dtype_device_id (dtype, device_id, id),
                        KEY idx_status_logs_device_id_id (device_id, id),
                        KEY idx_status_logs_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS config_file_versions (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        file_path VARCHAR(512) NOT NULL,
                        device_type_label VARCHAR(191) NOT NULL,
                        device_name VARCHAR(191) NOT NULL,
                        filename VARCHAR(191) NOT NULL,
                        detail TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_file_path (file_path)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS linked_files (
                        id VARCHAR(191) PRIMARY KEY,
                        owner_kind VARCHAR(64) NOT NULL,
                        owner_id VARCHAR(191) NOT NULL,
                        module_code VARCHAR(64) NOT NULL,
                        category VARCHAR(64) NOT NULL,
                        filename VARCHAR(255) NOT NULL,
                        stored_path VARCHAR(512) NOT NULL,
                        mime_type VARCHAR(191) NOT NULL DEFAULT '',
                        size_bytes BIGINT NOT NULL DEFAULT 0,
                        sha256 CHAR(64) NOT NULL DEFAULT '',
                        version_label VARCHAR(191) NOT NULL DEFAULT '',
                        detail TEXT NOT NULL,
                        metadata_json LONGTEXT NOT NULL,
                        sync_status VARCHAR(32) NOT NULL DEFAULT 'local_only',
                        sync_error TEXT NOT NULL,
                        created_by VARCHAR(191) NOT NULL DEFAULT '',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_linked_files_stored_path (stored_path),
                        KEY idx_linked_files_owner_category_updated (owner_kind, owner_id, category, updated_at),
                        KEY idx_linked_files_module_category (module_code, category)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS storage_targets (
                        id VARCHAR(191) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        service_code VARCHAR(191) NOT NULL,
                        service_label VARCHAR(191) NOT NULL,
                        kind VARCHAR(64) NOT NULL DEFAULT 'smb3',
                        remote_path TEXT NOT NULL,
                        username VARCHAR(191) NOT NULL DEFAULT '',
                        secret_ref VARCHAR(191) NOT NULL DEFAULT '',
                        local_mount_path VARCHAR(512) NOT NULL DEFAULT '',
                        auto_mount_enabled TINYINT(1) NOT NULL DEFAULT 1,
                        status VARCHAR(64) NOT NULL DEFAULT 'configured',
                        last_error TEXT NOT NULL,
                        last_checked_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        KEY idx_storage_targets_service (service_code, label)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sync_source_profiles (
                        id VARCHAR(64) NOT NULL PRIMARY KEY,
                        source_kind VARCHAR(32) NOT NULL DEFAULT 'active_directory',
                        code VARCHAR(64) NOT NULL,
                        label VARCHAR(191) NOT NULL,
                        target_kind VARCHAR(64) NOT NULL DEFAULT 'users',
                        search_base TEXT NOT NULL,
                        search_filter TEXT NOT NULL,
                        selected_attributes_json LONGTEXT NOT NULL,
                        options_json LONGTEXT NOT NULL,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_sync_source_profile_code (source_kind, code),
                        KEY idx_sync_source_profiles_source_target (source_kind, target_kind),
                        KEY idx_sync_source_profiles_active (source_kind, is_active)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sync_source_cache_entries (
                        id VARCHAR(64) NOT NULL PRIMARY KEY,
                        source_kind VARCHAR(32) NOT NULL DEFAULT 'active_directory',
                        target_kind VARCHAR(64) NOT NULL,
                        external_id VARCHAR(512) NOT NULL,
                        display_label VARCHAR(512) NOT NULL DEFAULT '',
                        payload_json LONGTEXT NOT NULL,
                        synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_sync_source_cache_entry (source_kind, target_kind, external_id),
                        KEY idx_sync_source_cache_kind_synced (source_kind, target_kind, synced_at),
                        KEY idx_sync_source_cache_label (source_kind, target_kind, display_label)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        token VARCHAR(255) PRIMARY KEY,
                        subject VARCHAR(255) NOT NULL,
                        created_at VARCHAR(64) NOT NULL,
                        expires_at VARCHAR(64) NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS app_settings (
                        setting_key VARCHAR(191) PRIMARY KEY,
                        payload_json LONGTEXT NOT NULL,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS dashboard_preferences (
                        dashboard_scope VARCHAR(80) NOT NULL,
                        card_id VARCHAR(160) NOT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        is_hidden TINYINT(1) NOT NULL DEFAULT 0,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        PRIMARY KEY (dashboard_scope, card_id),
                        KEY idx_dashboard_preferences_scope_order (dashboard_scope, sort_order, card_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notification_tasks (
                        id VARCHAR(64) PRIMARY KEY,
                        source_service_code VARCHAR(191) NOT NULL DEFAULT '',
                        source_record_id VARCHAR(191) NOT NULL DEFAULT '',
                        trigger_field_key VARCHAR(191) NOT NULL DEFAULT '',
                        trigger_value VARCHAR(191) NOT NULL DEFAULT '',
                        title VARCHAR(255) NOT NULL DEFAULT '',
                        message TEXT NOT NULL,
                        due_at DATETIME NULL,
                        status VARCHAR(32) NOT NULL DEFAULT 'pending',
                        sent_at DATETIME NULL,
                        completed_at DATETIME NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_notification_task_source_trigger (source_service_code, source_record_id, trigger_field_key, trigger_value),
                        KEY idx_notification_tasks_due_status (status, due_at),
                        KEY idx_notification_tasks_source (source_service_code, source_record_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                CREATE TABLE IF NOT EXISTS auth_users (
                    subject VARCHAR(255) PRIMARY KEY,
                    label VARCHAR(255) NOT NULL DEFAULT '',
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    password_hash TEXT NOT NULL,
                    must_change_password TINYINT(1) NOT NULL DEFAULT 1
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_roles (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        is_system TINYINT(1) NOT NULL DEFAULT 0,
                        sort_order INT NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_modules (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        route_path VARCHAR(191) NOT NULL,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        sort_order INT NOT NULL DEFAULT 0
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_user_roles (
                        subject VARCHAR(255) NOT NULL,
                        role_code VARCHAR(64) NOT NULL,
                        PRIMARY KEY(subject, role_code),
                        CONSTRAINT fk_auth_user_roles_subject FOREIGN KEY (subject)
                            REFERENCES auth_users(subject) ON DELETE CASCADE,
                        CONSTRAINT fk_auth_user_roles_role FOREIGN KEY (role_code)
                            REFERENCES auth_roles(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS auth_role_modules (
                        role_code VARCHAR(64) NOT NULL,
                        module_code VARCHAR(64) NOT NULL,
                        PRIMARY KEY(role_code, module_code),
                        CONSTRAINT fk_auth_role_modules_role FOREIGN KEY (role_code)
                            REFERENCES auth_roles(code) ON DELETE CASCADE,
                        CONSTRAINT fk_auth_role_modules_module FOREIGN KEY (module_code)
                            REFERENCES auth_modules(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_services (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        credentials_enabled TINYINT(1) NOT NULL DEFAULT 0,
                        child_enabled TINYINT(1) NOT NULL DEFAULT 0,
                        child_label VARCHAR(191) NOT NULL DEFAULT 'Elements lies',
                        sort_order INT NOT NULL DEFAULT 100,
                        icon VARCHAR(64) NOT NULL DEFAULT '',
                        color VARCHAR(32) NOT NULL DEFAULT '',
                        description TEXT NOT NULL,
                        treeview_config LONGTEXT NOT NULL,
                        allow_export TINYINT(1) NOT NULL DEFAULT 1,
                        allow_import TINYINT(1) NOT NULL DEFAULT 1,
                        created_at DATETIME NULL,
                        updated_at DATETIME NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_fields (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        service_code VARCHAR(64) NOT NULL,
                        field_key VARCHAR(191) NOT NULL,
                        label VARCHAR(191) NOT NULL,
                        field_kind VARCHAR(64) NOT NULL,
                        required TINYINT(1) NOT NULL DEFAULT 0,
                        options TEXT NOT NULL,
                        default_value TEXT NOT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        list_source_kind VARCHAR(16) NOT NULL DEFAULT 'local',
                        shared_list_code VARCHAR(64) NOT NULL DEFAULT '',
                        show_in_list TINYINT(1) NOT NULL DEFAULT 1,
                        searchable TINYINT(1) NOT NULL DEFAULT 1,
                        unique_value TINYINT(1) NOT NULL DEFAULT 0,
                        placeholder VARCHAR(255) NOT NULL DEFAULT '',
                        help_text TEXT NOT NULL,
                        min_value DOUBLE NULL,
                        max_value DOUBLE NULL,
                        track_history TINYINT(1) NOT NULL DEFAULT 0,
                        inline_editable TINYINT(1) NOT NULL DEFAULT 0,
                        quick_filter TINYINT(1) NOT NULL DEFAULT 0,
                        UNIQUE KEY uq_custom_service_field (service_code, field_key),
                        CONSTRAINT fk_custom_service_fields_code FOREIGN KEY (service_code)
                            REFERENCES custom_services(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS shared_lists (
                        code VARCHAR(64) PRIMARY KEY,
                        label VARCHAR(191) NOT NULL,
                        is_system TINYINT(1) NOT NULL DEFAULT 0,
                        sort_order INT NOT NULL DEFAULT 100
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS shared_list_items (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        list_code VARCHAR(64) NOT NULL,
                        item_code VARCHAR(191) NOT NULL,
                        item_label VARCHAR(191) NOT NULL,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        sort_order INT NOT NULL DEFAULT 100,
                        UNIQUE KEY uq_shared_list_item (list_code, item_code),
                        CONSTRAINT fk_shared_list_items_code FOREIGN KEY (list_code)
                            REFERENCES shared_lists(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS organization_units (
                        id VARCHAR(191) PRIMARY KEY,
                        parent_id VARCHAR(191) NULL,
                        code VARCHAR(191) NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        display_path TEXT NOT NULL,
                        source_kind VARCHAR(32) NOT NULL DEFAULT 'manual',
                        external_id VARCHAR(191) NOT NULL DEFAULT '',
                        distinguished_name TEXT NOT NULL,
                        sync_status VARCHAR(32) NOT NULL DEFAULT 'active',
                        trashed_at DATETIME NULL,
                        trash_reason TEXT NOT NULL,
                        synced_at DATETIME NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        UNIQUE KEY uq_organization_units_source_external (source_kind, external_id),
                        KEY idx_organization_units_parent (parent_id),
                        KEY idx_organization_units_status (sync_status),
                        CONSTRAINT fk_organization_units_parent FOREIGN KEY (parent_id)
                            REFERENCES organization_units(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS directory_users (
                        id VARCHAR(191) PRIMARY KEY,
                        organization_unit_id VARCHAR(191) NULL,
                        login VARCHAR(191) NOT NULL,
                        display_name VARCHAR(255) NOT NULL,
                        first_name VARCHAR(191) NOT NULL DEFAULT '',
                        last_name VARCHAR(191) NOT NULL DEFAULT '',
                        email VARCHAR(255) NOT NULL DEFAULT '',
                        source_kind VARCHAR(32) NOT NULL DEFAULT 'manual',
                        external_id VARCHAR(191) NOT NULL DEFAULT '',
                        distinguished_name TEXT NOT NULL,
                        sync_status VARCHAR(32) NOT NULL DEFAULT 'active',
                        trashed_at DATETIME NULL,
                        trash_reason TEXT NOT NULL,
                        synced_at DATETIME NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        UNIQUE KEY uq_directory_users_source_external (source_kind, external_id),
                        KEY idx_directory_users_login (login),
                        KEY idx_directory_users_ou (organization_unit_id),
                        KEY idx_directory_users_status (sync_status),
                        CONSTRAINT fk_directory_users_ou FOREIGN KEY (organization_unit_id)
                            REFERENCES organization_units(id) ON DELETE SET NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_records (
                        id VARCHAR(191) PRIMARY KEY,
                        service_code VARCHAR(64) NOT NULL,
                        payload_json LONGTEXT NOT NULL,
                        sync_source_kind VARCHAR(32) NOT NULL DEFAULT '',
                        sync_target_kind VARCHAR(64) NOT NULL DEFAULT '',
                        sync_external_id VARCHAR(191) NOT NULL DEFAULT '',
                        sync_status VARCHAR(32) NOT NULL DEFAULT 'active',
                        trashed_at DATETIME NULL,
                        trash_reason TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        KEY idx_custom_service_records_service_updated (service_code, updated_at),
                        KEY idx_custom_service_records_sync (service_code, sync_source_kind, sync_target_kind, sync_status),
                        CONSTRAINT fk_custom_service_records_code FOREIGN KEY (service_code)
                            REFERENCES custom_services(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_children (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        record_id VARCHAR(191) NOT NULL,
                        child_name VARCHAR(255) NOT NULL,
                        child_code VARCHAR(255) NOT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        CONSTRAINT fk_custom_service_children_record FOREIGN KEY (record_id)
                            REFERENCES custom_service_records(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_record_index (
                        record_id VARCHAR(191) NOT NULL,
                        service_code VARCHAR(64) NOT NULL,
                        label_value VARCHAR(500) NOT NULL DEFAULT '',
                        search_blob TEXT NOT NULL,
                        indexed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (record_id),
                        KEY idx_csri_service_label (service_code, label_value),
                        KEY idx_csri_service_indexed (service_code, indexed_at),
                        FULLTEXT KEY ft_csri_search_blob (search_blob),
                        CONSTRAINT fk_csri_record FOREIGN KEY (record_id)
                            REFERENCES custom_service_records(id) ON DELETE CASCADE,
                        CONSTRAINT fk_csri_service FOREIGN KEY (service_code)
                            REFERENCES custom_services(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_record_history (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        service_code VARCHAR(64) NOT NULL,
                        record_id VARCHAR(191) NOT NULL,
                        field_key VARCHAR(191) NOT NULL,
                        old_value TEXT NOT NULL,
                        new_value TEXT NOT NULL,
                        changed_at DATETIME NOT NULL,
                        changed_by VARCHAR(191) NOT NULL DEFAULT '',
                        change_source VARCHAR(64) NOT NULL DEFAULT '',
                        KEY idx_csrh_record_changed (record_id, changed_at),
                        KEY idx_csrh_service_field_changed (service_code, field_key, changed_at),
                        CONSTRAINT fk_csrh_record FOREIGN KEY (record_id)
                            REFERENCES custom_service_records(id) ON DELETE CASCADE,
                        CONSTRAINT fk_csrh_service FOREIGN KEY (service_code)
                            REFERENCES custom_services(code) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_relations (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        source_service_code VARCHAR(64) NOT NULL,
                        target_service_code VARCHAR(64) NOT NULL,
                        verb VARCHAR(191) NOT NULL DEFAULT 'est lie a',
                        cardinality VARCHAR(32) NOT NULL DEFAULT 'many_to_one',
                        direction VARCHAR(16) NOT NULL DEFAULT 'out',
                        display_label VARCHAR(191) NOT NULL DEFAULT '',
                        required TINYINT(1) NOT NULL DEFAULT 0,
                        is_active TINYINT(1) NOT NULL DEFAULT 1,
                        source_x INT NULL,
                        source_y INT NULL,
                        target_x INT NULL,
                        target_y INT NULL,
                        sort_order INT NOT NULL DEFAULT 0,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_custom_service_relation (
                            source_service_code,
                            target_service_code,
                            cardinality,
                            direction
                        ),
                        KEY idx_custom_service_relations_source (source_service_code),
                        KEY idx_custom_service_relations_target (target_service_code)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS custom_service_relation_links (
                        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        relation_id BIGINT UNSIGNED NOT NULL,
                        source_record_id VARCHAR(191) NOT NULL,
                        target_record_id VARCHAR(191) NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        UNIQUE KEY uq_custom_service_relation_link (relation_id, source_record_id, target_record_id),
                        KEY idx_custom_service_relation_links_source (relation_id, source_record_id),
                        KEY idx_custom_service_relation_links_target (relation_id, target_record_id),
                        CONSTRAINT fk_csrl_relation FOREIGN KEY (relation_id)
                            REFERENCES custom_service_relations(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                    """
                )
            manager._ensure_status_logs_columns(conn)
            manager._ensure_devices_columns(conn)
            manager._ensure_device_type_fields_columns(conn)
            manager._ensure_device_type_actions_columns(conn)
            manager._ensure_device_types_columns(conn)
            manager._ensure_auth_users_columns(conn)
            manager._ensure_custom_service_columns(conn)
            manager._ensure_custom_service_field_columns(conn)
            manager._ensure_directory_schema(conn)
            manager._ensure_devices_indexes(conn)
            manager._ensure_status_logs_indexes(conn)
            manager._ensure_custom_service_record_indexes(conn)
            manager._ensure_custom_service_history_schema(conn)
            manager._ensure_custom_service_relation_schema(conn)
            manager._ensure_custom_service_relation_link_schema(conn)
            manager._ensure_sync_source_profile_schema(conn)
            manager._ensure_sync_source_cache_schema(conn)
            MariaDBBootstrapper.migrate_legacy_dashboard_settings(conn)
            manager._cleanup_reserved_custom_services(conn)
            conn.commit()

            manager._seed_default_device_types(conn)
            manager._ensure_default_schema_rows(conn)
            manager._ensure_os_field_rows(conn)
            manager._ensure_action_os_scope_rows(conn)
            manager._ensure_auth_rbac_rows(conn)
            MariaDBBootstrapper.ensure_email_service_rows(conn)
            manager._sync_custom_service_auth_modules(conn)
            MariaDBBootstrapper.ensure_system_relation_rows(conn)
            manager._ensure_shared_list_rows(conn)

            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM devices")
                count = int(cursor.fetchone()[0] or 0)
            if count == 0:
                manager._seed_from_json(conn)

    @staticmethod
    def _column_exists(conn, *, db_name: str, table_name: str, column_name: str) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
                """,
                (db_name, table_name, column_name),
            )
            row = cursor.fetchone()
            return bool(int(row[0] if row else 0))

    @staticmethod
    def _index_exists(conn, *, db_name: str, table_name: str, index_name: str) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s
                """,
                (db_name, table_name, index_name),
            )
            row = cursor.fetchone()
            return bool(int(row[0] if row else 0))

    @staticmethod
    def ensure_status_logs_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="status_logs", column_name="event_kind"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD COLUMN event_kind VARCHAR(64) NOT NULL DEFAULT 'status_change'")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="status_logs", column_name="details"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD COLUMN details TEXT NOT NULL")

    @staticmethod
    def ensure_status_logs_indexes(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._index_exists(
            conn,
            db_name=db_name,
            table_name="status_logs",
            index_name="idx_status_logs_dtype_device_id",
        ):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD INDEX idx_status_logs_dtype_device_id (dtype, device_id, id)")
        if not MariaDBBootstrapper._index_exists(
            conn,
            db_name=db_name,
            table_name="status_logs",
            index_name="idx_status_logs_device_id_id",
        ):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD INDEX idx_status_logs_device_id_id (device_id, id)")
        if not MariaDBBootstrapper._index_exists(
            conn,
            db_name=db_name,
            table_name="status_logs",
            index_name="idx_status_logs_created_at",
        ):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE status_logs ADD INDEX idx_status_logs_created_at (created_at)")

    @staticmethod
    def ensure_devices_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="devices", column_name="custom_data"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE devices ADD COLUMN custom_data LONGTEXT NOT NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="devices", column_name="device_login"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE devices ADD COLUMN device_login VARCHAR(191) NOT NULL DEFAULT ''")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="devices", column_name="device_password"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE devices ADD COLUMN device_password VARCHAR(1024) NOT NULL DEFAULT ''")

    @staticmethod
    def ensure_device_type_fields_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="device_type_fields", column_name="show_in_table"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE device_type_fields ADD COLUMN show_in_table TINYINT(1) NOT NULL DEFAULT 0")
                cursor.execute(
                    """
                    UPDATE device_type_fields
                    SET show_in_table = 1
                    WHERE field_key IN ('name', 'ip', 'device_login', 'device_password')
                    """
                )

    @staticmethod
    def ensure_devices_indexes(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._index_exists(conn, db_name=db_name, table_name="devices", index_name="idx_devices_dtype_ip"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE devices ADD INDEX idx_devices_dtype_ip (dtype, ip)")
        if not MariaDBBootstrapper._index_exists(conn, db_name=db_name, table_name="devices", index_name="idx_devices_dtype_name"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE devices ADD INDEX idx_devices_dtype_name (dtype, name)")

    @staticmethod
    def ensure_device_type_actions_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="device_type_actions", column_name="os_scope"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE device_type_actions ADD COLUMN os_scope TEXT NOT NULL")

    @staticmethod
    def ensure_device_types_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="device_types", column_name="config_backups_enabled"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE device_types ADD COLUMN config_backups_enabled TINYINT(1) DEFAULT NULL")

    @staticmethod
    def ensure_auth_users_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="auth_users", column_name="password_hash"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE auth_users ADD COLUMN password_hash TEXT NOT NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="auth_users", column_name="must_change_password"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE auth_users ADD COLUMN must_change_password TINYINT(1) NOT NULL DEFAULT 1")

    @staticmethod
    def ensure_custom_service_field_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="list_source_kind"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN list_source_kind VARCHAR(16) NOT NULL DEFAULT 'local'")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="shared_list_code"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN shared_list_code VARCHAR(64) NOT NULL DEFAULT ''")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="show_in_list"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN show_in_list TINYINT(1) NOT NULL DEFAULT 1")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="searchable"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN searchable TINYINT(1) NOT NULL DEFAULT 1")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="unique_value"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN unique_value TINYINT(1) NOT NULL DEFAULT 0")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="placeholder"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN placeholder VARCHAR(255) NOT NULL DEFAULT ''")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="help_text"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN help_text TEXT NOT NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="min_value"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN min_value DOUBLE NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="max_value"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN max_value DOUBLE NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="track_history"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN track_history TINYINT(1) NOT NULL DEFAULT 0")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="inline_editable"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN inline_editable TINYINT(1) NOT NULL DEFAULT 0")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_fields", column_name="quick_filter"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_service_fields ADD COLUMN quick_filter TINYINT(1) NOT NULL DEFAULT 0")

    @staticmethod
    def ensure_custom_service_columns(conn, db_name: str) -> None:
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="is_active"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="credentials_enabled"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN credentials_enabled TINYINT(1) NOT NULL DEFAULT 0")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="icon"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN icon VARCHAR(64) NOT NULL DEFAULT ''")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="color"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN color VARCHAR(32) NOT NULL DEFAULT ''")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="description"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN description TEXT NOT NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="treeview_config"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN treeview_config LONGTEXT NOT NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="allow_export"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN allow_export TINYINT(1) NOT NULL DEFAULT 1")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="allow_import"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN allow_import TINYINT(1) NOT NULL DEFAULT 1")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="created_at"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN created_at DATETIME NULL")
        if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_services", column_name="updated_at"):
            with conn.cursor() as cursor:
                cursor.execute("ALTER TABLE custom_services ADD COLUMN updated_at DATETIME NULL")

    @staticmethod
    def ensure_directory_schema(conn, db_name: str) -> None:
        del db_name
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_units (
                    id VARCHAR(191) PRIMARY KEY,
                    parent_id VARCHAR(191) NULL,
                    code VARCHAR(191) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    display_path TEXT NOT NULL,
                    source_kind VARCHAR(32) NOT NULL DEFAULT 'manual',
                    external_id VARCHAR(191) NOT NULL DEFAULT '',
                    distinguished_name TEXT NOT NULL,
                    sync_status VARCHAR(32) NOT NULL DEFAULT 'active',
                    trashed_at DATETIME NULL,
                    trash_reason TEXT NOT NULL,
                    synced_at DATETIME NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uq_organization_units_source_external (source_kind, external_id),
                    KEY idx_organization_units_parent (parent_id),
                    KEY idx_organization_units_status (sync_status),
                    CONSTRAINT fk_organization_units_parent FOREIGN KEY (parent_id)
                        REFERENCES organization_units(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS directory_users (
                    id VARCHAR(191) PRIMARY KEY,
                    organization_unit_id VARCHAR(191) NULL,
                    login VARCHAR(191) NOT NULL,
                    display_name VARCHAR(255) NOT NULL,
                    first_name VARCHAR(191) NOT NULL DEFAULT '',
                    last_name VARCHAR(191) NOT NULL DEFAULT '',
                    email VARCHAR(255) NOT NULL DEFAULT '',
                    source_kind VARCHAR(32) NOT NULL DEFAULT 'manual',
                    external_id VARCHAR(191) NOT NULL DEFAULT '',
                    distinguished_name TEXT NOT NULL,
                    sync_status VARCHAR(32) NOT NULL DEFAULT 'active',
                    trashed_at DATETIME NULL,
                    trash_reason TEXT NOT NULL,
                    synced_at DATETIME NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    UNIQUE KEY uq_directory_users_source_external (source_kind, external_id),
                    KEY idx_directory_users_login (login),
                    KEY idx_directory_users_ou (organization_unit_id),
                    KEY idx_directory_users_status (sync_status),
                    CONSTRAINT fk_directory_users_ou FOREIGN KEY (organization_unit_id)
                        REFERENCES organization_units(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

    @staticmethod
    def cleanup_reserved_custom_services(conn, manager_cls) -> None:
        reserved_codes = tuple(sorted(getattr(manager_cls, "RESERVED_SYSTEM_ENTITY_CODES", set()) or []))
        if not reserved_codes:
            return
        placeholders = ", ".join(["%s"] * len(reserved_codes))
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                DELETE l
                FROM custom_service_relation_links l
                JOIN custom_service_records r ON r.id = l.source_record_id OR r.id = l.target_record_id
                WHERE r.service_code IN ({placeholders})
                """,
                reserved_codes,
            )
            cursor.execute(f"DELETE FROM custom_service_records WHERE service_code IN ({placeholders})", reserved_codes)
            cursor.execute(f"DELETE FROM custom_services WHERE code IN ({placeholders})", reserved_codes)

    @staticmethod
    def ensure_custom_service_record_indexes(conn, db_name: str) -> None:
        for column_name, ddl in {
            "sync_source_kind": "ALTER TABLE custom_service_records ADD COLUMN sync_source_kind VARCHAR(32) NOT NULL DEFAULT ''",
            "sync_target_kind": "ALTER TABLE custom_service_records ADD COLUMN sync_target_kind VARCHAR(64) NOT NULL DEFAULT ''",
            "sync_external_id": "ALTER TABLE custom_service_records ADD COLUMN sync_external_id VARCHAR(191) NOT NULL DEFAULT ''",
            "sync_status": "ALTER TABLE custom_service_records ADD COLUMN sync_status VARCHAR(32) NOT NULL DEFAULT 'active'",
            "trashed_at": "ALTER TABLE custom_service_records ADD COLUMN trashed_at DATETIME NULL",
            "trash_reason": "ALTER TABLE custom_service_records ADD COLUMN trash_reason TEXT NOT NULL",
        }.items():
            if not MariaDBBootstrapper._column_exists(conn, db_name=db_name, table_name="custom_service_records", column_name=column_name):
                with conn.cursor() as cursor:
                    cursor.execute(ddl)
        if not MariaDBBootstrapper._index_exists(
            conn,
            db_name=db_name,
            table_name="custom_service_records",
            index_name="idx_custom_service_records_service_updated",
        ):
            with conn.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE custom_service_records ADD INDEX idx_custom_service_records_service_updated (service_code, updated_at)"
                )
        if not MariaDBBootstrapper._index_exists(
            conn,
            db_name=db_name,
            table_name="custom_service_records",
            index_name="idx_custom_service_records_sync",
        ):
            with conn.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE custom_service_records ADD INDEX idx_custom_service_records_sync (service_code, sync_source_kind, sync_target_kind, sync_status)"
                )

    @staticmethod
    def ensure_custom_service_history_schema(conn, db_name: str) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_service_record_history (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    service_code VARCHAR(64) NOT NULL,
                    record_id VARCHAR(191) NOT NULL,
                    field_key VARCHAR(191) NOT NULL,
                    old_value TEXT NOT NULL,
                    new_value TEXT NOT NULL,
                    changed_at DATETIME NOT NULL,
                    changed_by VARCHAR(191) NOT NULL DEFAULT '',
                    change_source VARCHAR(64) NOT NULL DEFAULT '',
                    KEY idx_csrh_record_changed (record_id, changed_at),
                    KEY idx_csrh_service_field_changed (service_code, field_key, changed_at),
                    CONSTRAINT fk_csrh_record FOREIGN KEY (record_id)
                        REFERENCES custom_service_records(id) ON DELETE CASCADE,
                    CONSTRAINT fk_csrh_service FOREIGN KEY (service_code)
                        REFERENCES custom_services(code) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )

    @staticmethod
    def ensure_custom_service_relation_schema(conn, db_name: str) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_service_relations (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    source_service_code VARCHAR(64) NOT NULL,
                    target_service_code VARCHAR(64) NOT NULL,
                    verb VARCHAR(191) NOT NULL DEFAULT 'est lie a',
                    cardinality VARCHAR(32) NOT NULL DEFAULT 'many_to_one',
                    direction VARCHAR(16) NOT NULL DEFAULT 'out',
                    display_label VARCHAR(191) NOT NULL DEFAULT '',
                    required TINYINT(1) NOT NULL DEFAULT 0,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    source_x INT NULL,
                    source_y INT NULL,
                    target_x INT NULL,
                    target_y INT NULL,
                    sort_order INT NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_custom_service_relation (
                        source_service_code,
                        target_service_code,
                        cardinality,
                        direction
                    ),
                    KEY idx_custom_service_relations_source (source_service_code),
                    KEY idx_custom_service_relations_target (target_service_code)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            for constraint_name in ("fk_custom_service_relations_source", "fk_custom_service_relations_target"):
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
                    WHERE TABLE_SCHEMA = %s
                      AND TABLE_NAME = 'custom_service_relations'
                      AND CONSTRAINT_NAME = %s
                      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                    """,
                    (db_name, constraint_name),
                )
                row = cursor.fetchone()
                if bool(int(row[0] if row else 0)):
                    cursor.execute(f"ALTER TABLE custom_service_relations DROP FOREIGN KEY {constraint_name}")
        expected_columns = {
            "verb": "ALTER TABLE custom_service_relations ADD COLUMN verb VARCHAR(191) NOT NULL DEFAULT 'est lie a'",
            "cardinality": "ALTER TABLE custom_service_relations ADD COLUMN cardinality VARCHAR(32) NOT NULL DEFAULT 'many_to_one'",
            "direction": "ALTER TABLE custom_service_relations ADD COLUMN direction VARCHAR(16) NOT NULL DEFAULT 'out'",
            "display_label": "ALTER TABLE custom_service_relations ADD COLUMN display_label VARCHAR(191) NOT NULL DEFAULT ''",
            "required": "ALTER TABLE custom_service_relations ADD COLUMN required TINYINT(1) NOT NULL DEFAULT 0",
            "is_active": "ALTER TABLE custom_service_relations ADD COLUMN is_active TINYINT(1) NOT NULL DEFAULT 1",
            "source_x": "ALTER TABLE custom_service_relations ADD COLUMN source_x INT NULL",
            "source_y": "ALTER TABLE custom_service_relations ADD COLUMN source_y INT NULL",
            "target_x": "ALTER TABLE custom_service_relations ADD COLUMN target_x INT NULL",
            "target_y": "ALTER TABLE custom_service_relations ADD COLUMN target_y INT NULL",
            "sort_order": "ALTER TABLE custom_service_relations ADD COLUMN sort_order INT NOT NULL DEFAULT 0",
            "created_at": "ALTER TABLE custom_service_relations ADD COLUMN created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "ALTER TABLE custom_service_relations ADD COLUMN updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        }
        for column_name, statement in expected_columns.items():
            if not MariaDBBootstrapper._column_exists(
                conn,
                db_name=db_name,
                table_name="custom_service_relations",
                column_name=column_name,
            ):
                with conn.cursor() as cursor:
                    cursor.execute(statement)
        expected_indexes = {
            "idx_custom_service_relations_source": (
                "ALTER TABLE custom_service_relations "
                "ADD INDEX idx_custom_service_relations_source (source_service_code)"
            ),
            "idx_custom_service_relations_target": (
                "ALTER TABLE custom_service_relations "
                "ADD INDEX idx_custom_service_relations_target (target_service_code)"
            ),
        }
        for index_name, statement in expected_indexes.items():
            if not MariaDBBootstrapper._index_exists(
                conn,
                db_name=db_name,
                table_name="custom_service_relations",
                index_name=index_name,
            ):
                with conn.cursor() as cursor:
                    cursor.execute(statement)

    @staticmethod
    def ensure_custom_service_relation_link_schema(conn, db_name: str) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS custom_service_relation_links (
                    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    relation_id BIGINT UNSIGNED NOT NULL,
                    source_record_id VARCHAR(191) NOT NULL,
                    target_record_id VARCHAR(191) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_custom_service_relation_link (relation_id, source_record_id, target_record_id),
                    KEY idx_custom_service_relation_links_source (relation_id, source_record_id),
                    KEY idx_custom_service_relation_links_target (relation_id, target_record_id),
                    CONSTRAINT fk_csrl_relation FOREIGN KEY (relation_id)
                        REFERENCES custom_service_relations(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            for constraint_name in ("fk_csrl_source_record", "fk_csrl_target_record"):
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.TABLE_CONSTRAINTS
                    WHERE CONSTRAINT_SCHEMA = %s
                      AND TABLE_NAME = 'custom_service_relation_links'
                      AND CONSTRAINT_NAME = %s
                      AND CONSTRAINT_TYPE = 'FOREIGN KEY'
                    """,
                    (db_name, constraint_name),
                )
                if int((cursor.fetchone() or (0,))[0] or 0) > 0:
                    cursor.execute(f"ALTER TABLE custom_service_relation_links DROP FOREIGN KEY {constraint_name}")
        expected_indexes = {
            "idx_custom_service_relation_links_source": (
                "ALTER TABLE custom_service_relation_links "
                "ADD INDEX idx_custom_service_relation_links_source (relation_id, source_record_id)"
            ),
            "idx_custom_service_relation_links_target": (
                "ALTER TABLE custom_service_relation_links "
                "ADD INDEX idx_custom_service_relation_links_target (relation_id, target_record_id)"
            ),
        }
        for index_name, statement in expected_indexes.items():
            if not MariaDBBootstrapper._index_exists(
                conn,
                db_name=db_name,
                table_name="custom_service_relation_links",
                index_name=index_name,
            ):
                with conn.cursor() as cursor:
                    cursor.execute(statement)

    @staticmethod
    def ensure_sync_source_profile_schema(conn, db_name: str) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_source_profiles (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    source_kind VARCHAR(32) NOT NULL DEFAULT 'active_directory',
                    code VARCHAR(64) NOT NULL,
                    label VARCHAR(191) NOT NULL,
                    target_kind VARCHAR(64) NOT NULL DEFAULT 'users',
                    search_base TEXT NOT NULL,
                    search_filter TEXT NOT NULL,
                    selected_attributes_json LONGTEXT NOT NULL,
                    options_json LONGTEXT NOT NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_sync_source_profile_code (source_kind, code),
                    KEY idx_sync_source_profiles_source_target (source_kind, target_kind),
                    KEY idx_sync_source_profiles_active (source_kind, is_active)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        expected_indexes = {
            "idx_sync_source_profiles_source_target": (
                "ALTER TABLE sync_source_profiles "
                "ADD INDEX idx_sync_source_profiles_source_target (source_kind, target_kind)"
            ),
            "idx_sync_source_profiles_active": (
                "ALTER TABLE sync_source_profiles "
                "ADD INDEX idx_sync_source_profiles_active (source_kind, is_active)"
            ),
        }
        for index_name, statement in expected_indexes.items():
            if not MariaDBBootstrapper._index_exists(
                conn,
                db_name=db_name,
                table_name="sync_source_profiles",
                index_name=index_name,
            ):
                with conn.cursor() as cursor:
                    cursor.execute(statement)

    @staticmethod
    def ensure_sync_source_cache_schema(conn, db_name: str) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_source_cache_entries (
                    id VARCHAR(64) NOT NULL PRIMARY KEY,
                    source_kind VARCHAR(32) NOT NULL DEFAULT 'active_directory',
                    target_kind VARCHAR(64) NOT NULL,
                    external_id VARCHAR(512) NOT NULL,
                    display_label VARCHAR(512) NOT NULL DEFAULT '',
                    payload_json LONGTEXT NOT NULL,
                    synced_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY uq_sync_source_cache_entry (source_kind, target_kind, external_id),
                    KEY idx_sync_source_cache_kind_synced (source_kind, target_kind, synced_at),
                    KEY idx_sync_source_cache_label (source_kind, target_kind, display_label)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
        expected_indexes = {
            "idx_sync_source_cache_kind_synced": (
                "ALTER TABLE sync_source_cache_entries "
                "ADD INDEX idx_sync_source_cache_kind_synced (source_kind, target_kind, synced_at)"
            ),
            "idx_sync_source_cache_label": (
                "ALTER TABLE sync_source_cache_entries "
                "ADD INDEX idx_sync_source_cache_label (source_kind, target_kind, display_label)"
            ),
        }
        for index_name, statement in expected_indexes.items():
            if not MariaDBBootstrapper._index_exists(
                conn,
                db_name=db_name,
                table_name="sync_source_cache_entries",
                index_name=index_name,
            ):
                with conn.cursor() as cursor:
                    cursor.execute(statement)

    @staticmethod
    def ensure_default_schema_rows(conn, manager_cls) -> None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'")
            fields_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'")
            actions_count = int(cursor.fetchone()[0] or 0)
            if fields_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, show_in_table, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("switch", "name", "Nom", "text", 1, "", "", 1, 10),
                        ("switch", "ip", "IP", "ip", 1, "", "", 1, 20),
                        ("switch", "description", "Description", "text", 0, "", "", 0, 30),
                        ("switch", "type", "OS", "choice", 1, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, 0, 40),
                        ("switch", "action_double_click", "Action double-clic", "choice", 0, "web,ssh,teamviewer,remote_desktop", "", 0, 60),
                    ],
                )
            if actions_count == 0:
                cursor.execute(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    ("switch", "web", "Ouvrir IP", "builtin", "web", manager_cls.ALL_OS_SCOPE, 10, 1),
                )
        conn.commit()

    @staticmethod
    def seed_from_json(conn) -> None:
        json_mgr = JSONFileManager()
        data = json_mgr.read_json_file()
        if not isinstance(data, dict):
            return

        rows: List[tuple] = []
        for dtype, items in data.items():
            if not isinstance(items, list):
                continue
            for item in items:
                rows.append(
                    (
                        str(item.get("id", "")),
                        str(dtype),
                        str(item.get("name", "")),
                        str(item.get("ip", "")),
                        str(item.get("description", "")),
                        1 if bool(item.get("notify", True)) else 0,
                        str(item.get("id_Teamviewer", "")),
                        str(item.get("type", "")),
                        str(item.get("action_double_click", "")),
                        str(item.get("web_url", "")),
                        str(item.get("ssh_user", "")),
                        str(item.get("device_login", "")),
                        str(item.get("device_password", "")),
                        json.dumps(item.get("custom_data", {}), ensure_ascii=False),
                    )
                )

        if not rows:
            return

        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO devices (
                    id, dtype, name, ip, description, notify,
                    id_teamviewer, subtype, action_double_click, web_url, ssh_user,
                    device_login, device_password, custom_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    dtype=VALUES(dtype),
                    name=VALUES(name),
                    ip=VALUES(ip),
                    description=VALUES(description),
                    notify=VALUES(notify),
                    id_teamviewer=VALUES(id_teamviewer),
                    subtype=VALUES(subtype),
                    action_double_click=VALUES(action_double_click),
                    web_url=VALUES(web_url),
                    ssh_user=VALUES(ssh_user),
                    device_login=VALUES(device_login),
                    device_password=VALUES(device_password),
                    custom_data=VALUES(custom_data)
                """,
                rows,
            )
        conn.commit()
        log_with_timestamp(f"Migration JSON vers MariaDB terminee ({len(rows)} equipements).")

    @staticmethod
    def migrate_legacy_dashboard_settings(conn) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT payload_json FROM app_settings WHERE setting_key = 'notification_settings'"
            )
            row = cursor.fetchone()
            if not row:
                return
            try:
                payload = json.loads(str(row[0] or "{}"))
            except Exception:
                payload = {}
            if not isinstance(payload, dict):
                return
            raw_order = payload.pop("dashboard_cards_order_json", "")
            raw_hidden = payload.pop("dashboard_hidden_cards_json", "")
            if raw_order or raw_hidden:
                order_by_scope = MariaDBBootstrapper._decode_dashboard_scope_map(raw_order)
                hidden_by_scope = MariaDBBootstrapper._decode_dashboard_scope_map(raw_hidden)
                for scope in sorted(set(order_by_scope) | set(hidden_by_scope)):
                    ordered: list[str] = []
                    seen: set[str] = set()
                    for card_id in list(order_by_scope.get(scope, [])) + list(hidden_by_scope.get(scope, [])):
                        normalized = str(card_id or "").strip()
                        if not normalized or normalized in seen:
                            continue
                        seen.add(normalized)
                        ordered.append(normalized)
                    hidden = {str(card_id or "").strip() for card_id in hidden_by_scope.get(scope, []) if str(card_id or "").strip()}
                    if not ordered:
                        continue
                    cursor.executemany(
                        """
                        INSERT INTO dashboard_preferences(dashboard_scope, card_id, sort_order, is_hidden)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            sort_order = VALUES(sort_order),
                            is_hidden = VALUES(is_hidden)
                        """,
                        [
                            (scope, card_id, index, 1 if card_id in hidden else 0)
                            for index, card_id in enumerate(ordered)
                        ],
                    )
                cursor.execute(
                    """
                    UPDATE app_settings
                    SET payload_json = %s
                    WHERE setting_key = 'notification_settings'
                    """,
                    (json.dumps(payload, ensure_ascii=False),),
                )

    @staticmethod
    def _decode_dashboard_scope_map(raw_value) -> dict[str, list[str]]:
        if not raw_value:
            return {}
        try:
            parsed = json.loads(str(raw_value)) if isinstance(raw_value, str) else raw_value
        except Exception:
            return {}
        if not isinstance(parsed, dict):
            return {}
        decoded: dict[str, list[str]] = {}
        for raw_scope, raw_items in parsed.items():
            scope = str(raw_scope or "").strip().lower()
            if not scope or not isinstance(raw_items, list):
                continue
            decoded[scope] = [str(item or "").strip() for item in raw_items if str(item or "").strip()]
        return decoded

    @staticmethod
    def ensure_shared_list_rows(conn) -> None:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT IGNORE INTO shared_lists(code, label, is_system, sort_order)
                VALUES ('services_mairie', 'Services de la mairie', 1, 10)
                """
            )
            cursor.executemany(
                """
                INSERT IGNORE INTO shared_list_items(list_code, item_code, item_label, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    ("services_mairie", "rh", "Ressources humaines", 1, 10),
                    ("services_mairie", "dsi", "Direction des systemes d'information", 1, 20),
                    ("services_mairie", "finances", "Finances", 1, 30),
                    ("services_mairie", "accueil", "Accueil", 1, 40),
                ],
            )
        conn.commit()

    @staticmethod
    def ensure_auth_rbac_rows(conn) -> None:
        default_sa_hash = MariaDBBootstrapper._default_hash_for_password("sa")
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_modules(code, label, route_path, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    ("monitoring", "Monitoring", "/monitoring", 1, 10),
                    ("imprimantes", "Imprimantes", "/imprimantes", 1, 30),
                    ("comptes", "Comptes techniques", "/comptes-techniques", 1, 40),
                    ("directory_agents", "Agents", "#directory=agents", 1, 45),
                    ("directory_services", "Services", "#directory=services", 1, 46),
                    ("admin", "Administration", "/admin", 1, 50),
                    ("users_admin", "Gestion utilisateurs", "/admin/users", 1, 60),
                ],
            )
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_roles(code, label, is_system, sort_order)
                VALUES (%s, %s, %s, %s)
                """,
                [
                    ("admin", "Administrateur", 1, 10),
                    ("technician", "Technicien", 1, 20),
                ],
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_users(subject, label, is_active, password_hash, must_change_password)
                VALUES ('sa', 'Super Admin', 1, %s, 1)
                """,
                (default_sa_hash,),
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_users(subject, label, is_active, password_hash, must_change_password)
                VALUES ('admin', 'Administrateur local', 1, '', 1)
                """
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_user_roles(subject, role_code)
                SELECT 'sa', 'admin'
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM auth_user_roles WHERE subject = 'sa'
                )
                """
            )
            cursor.execute(
                """
                DELETE FROM auth_user_roles
                WHERE subject = 'sa' AND role_code <> 'admin'
                """
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_user_roles(subject, role_code)
                VALUES ('sa', 'admin')
                """
            )
            cursor.execute(
                """
                INSERT IGNORE INTO auth_user_roles(subject, role_code)
                SELECT 'admin', 'admin'
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM auth_user_roles WHERE subject = 'admin'
                )
                """
            )
            cursor.execute(
                """
                DELETE FROM auth_role_modules
                WHERE module_code = 'interventions'
                """
            )
            cursor.execute(
                """
                DELETE FROM auth_modules
                WHERE code = 'interventions'
                """
            )
            cursor.execute("SELECT COUNT(*) FROM auth_role_modules")
            role_modules_count = int(cursor.fetchone()[0] or 0)
            if role_modules_count == 0:
                cursor.execute(
                    """
                    UPDATE auth_modules
                    SET is_active = CASE WHEN code IN ('monitoring', 'admin', 'users_admin') THEN 1 ELSE 0 END
                    WHERE code IN ('monitoring', 'imprimantes', 'comptes', 'admin', 'users_admin')
                    """
                )
                cursor.executemany(
                    """
                    INSERT IGNORE INTO auth_role_modules(role_code, module_code)
                    VALUES (%s, %s)
                    """,
                    [
                        ("admin", "monitoring"),
                        ("admin", "imprimantes"),
                        ("admin", "comptes"),
                        ("admin", "directory_agents"),
                        ("admin", "directory_services"),
                        ("admin", "admin"),
                        ("admin", "users_admin"),
                        ("technician", "monitoring"),
                        ("technician", "imprimantes"),
                        ("technician", "directory_agents"),
                        ("technician", "directory_services"),
                    ],
                )
            cursor.executemany(
                """
                INSERT IGNORE INTO auth_role_modules(role_code, module_code)
                VALUES (%s, %s)
                """,
                [
                    ("admin", "directory_agents"),
                    ("admin", "directory_services"),
                    ("technician", "directory_agents"),
                    ("technician", "directory_services"),
                ],
            )
        conn.commit()

    @staticmethod
    def ensure_email_service_rows(conn) -> None:
        now_iso = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        email_fields = [
            ("address", "Adresse email", "text", 1, "", "", 10, 1, 1, 1, "", "", 1, 1, 0),
            ("alias", "Alias", "text", 0, "", "", 20, 1, 1, 0, "", "", 0, 1, 0),
            ("type_compte", "Type de compte", "list", 0, "nominatif,generique,technique,partage", "nominatif", 30, 1, 1, 0, "", "", 0, 1, 1),
            ("service_reference", "Service reference", "text", 0, "", "", 40, 1, 1, 0, "", "", 0, 1, 0),
            ("status", "Statut", "list", 0, "Actif,A supprimer,Supprime", "Actif", 50, 1, 1, 0, "", "", 0, 1, 1),
            ("notes", "Notes", "text", 0, "", "", 60, 0, 1, 0, "", "", 0, 0, 0),
        ]
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO custom_services(
                    code, label, is_active, credentials_enabled, child_enabled, child_label, sort_order,
                    icon, color, description, treeview_config, allow_export, allow_import, created_at, updated_at
                )
                VALUES ('emails', 'Emails', 1, 1, 0, 'Agents lies', 47,
                        'mail', '', 'Module systeme des comptes email geres par prestataire.', '', 1, 1, %s, %s)
                ON DUPLICATE KEY UPDATE
                    label=VALUES(label),
                    is_active=1,
                    credentials_enabled=1,
                    child_enabled=VALUES(child_enabled),
                    child_label=VALUES(child_label),
                    sort_order=LEAST(sort_order, VALUES(sort_order)),
                    updated_at=VALUES(updated_at)
                """,
                (now_iso, now_iso),
            )
            cursor.executemany(
                """
                INSERT INTO custom_service_fields(
                    service_code, field_key, label, field_kind, required, options, default_value, sort_order,
                    list_source_kind, shared_list_code, show_in_list, searchable, unique_value,
                    placeholder, help_text, min_value, max_value, track_history, inline_editable, quick_filter
                )
                VALUES ('emails', %s, %s, %s, %s, %s, %s, %s,
                        'local', '', %s, %s, %s, %s, %s, NULL, NULL, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    label=VALUES(label),
                    field_kind=VALUES(field_kind),
                    required=VALUES(required),
                    options=VALUES(options),
                    default_value=VALUES(default_value),
                    sort_order=VALUES(sort_order),
                    show_in_list=VALUES(show_in_list),
                    searchable=VALUES(searchable),
                    unique_value=VALUES(unique_value),
                    placeholder=VALUES(placeholder),
                    help_text=VALUES(help_text),
                    track_history=VALUES(track_history),
                    inline_editable=VALUES(inline_editable),
                    quick_filter=VALUES(quick_filter)
                """,
                email_fields,
            )
            cursor.execute(
                """
                DELETE FROM custom_service_fields
                WHERE service_code = 'emails'
                  AND field_key IN ('provider', 'responsable', 'account_login')
                """
            )
        conn.commit()

    @staticmethod
    def ensure_system_relation_rows(conn) -> None:
        relation_seeds = [
            {
                "source": "utilisateurs",
                "target": "services",
                "verb": "appartient a",
                "label": "Agents / Services",
                "source_x": 120,
                "source_y": 180,
                "target_x": 520,
                "target_y": 180,
                "sort_order": 1,
            },
            {
                "source": "utilisateurs",
                "target": "emails",
                "verb": "possede",
                "label": "Agents / Emails",
                "source_x": 120,
                "source_y": 360,
                "target_x": 520,
                "target_y": 360,
                "sort_order": 2,
            },
        ]
        with conn.cursor() as cursor:
            for seed in relation_seeds:
                source = seed["source"]
                target = seed["target"]
                verb = seed["verb"]
                label = seed["label"]
                source_x = int(seed["source_x"])
                source_y = int(seed["source_y"])
                target_x = int(seed["target_x"])
                target_y = int(seed["target_y"])
                sort_order = int(seed["sort_order"])
                cursor.execute(
                    """
                    SELECT id
                    FROM custom_service_relations
                    WHERE source_service_code = %s
                      AND target_service_code = %s
                      AND direction = 'out'
                    ORDER BY id
                    """,
                    (source, target),
                )
                relation_ids = [int(row[0] or 0) for row in (cursor.fetchall() or []) if int(row[0] or 0) > 0]
                if relation_ids:
                    keeper_id = relation_ids[0]
                    duplicate_ids = relation_ids[1:]
                    if duplicate_ids:
                        placeholders = ",".join(["%s"] * len(duplicate_ids))
                        cursor.execute(
                            f"""
                            INSERT IGNORE INTO custom_service_relation_links(relation_id, source_record_id, target_record_id)
                            SELECT %s, source_record_id, target_record_id
                            FROM custom_service_relation_links
                            WHERE relation_id IN ({placeholders})
                            """,
                            [keeper_id, *duplicate_ids],
                        )
                        cursor.execute(
                            f"DELETE FROM custom_service_relation_links WHERE relation_id IN ({placeholders})",
                            duplicate_ids,
                        )
                        cursor.execute(
                            f"DELETE FROM custom_service_relations WHERE id IN ({placeholders})",
                            duplicate_ids,
                        )
                    cursor.execute(
                        """
                        UPDATE custom_service_relations
                        SET verb = %s,
                            cardinality = 'many_to_many',
                            display_label = %s,
                            required = 0,
                            is_active = 1,
                            source_x = COALESCE(source_x, %s),
                            source_y = COALESCE(source_y, %s),
                            target_x = COALESCE(target_x, %s),
                            target_y = COALESCE(target_y, %s),
                            sort_order = LEAST(sort_order, %s)
                        WHERE id = %s
                        """,
                        (verb, label, source_x, source_y, target_x, target_y, sort_order, keeper_id),
                    )
                    continue
                cursor.execute(
                    """
                    INSERT INTO custom_service_relations(
                        source_service_code, target_service_code, verb, cardinality, direction,
                        display_label, required, is_active, source_x, source_y, target_x, target_y, sort_order
                    )
                    VALUES (%s, %s, %s, 'many_to_many', 'out', %s, 0, 1, %s, %s, %s, %s, %s)
                    """,
                    (source, target, verb, label, source_x, source_y, target_x, target_y, sort_order),
                )
        conn.commit()

    @staticmethod
    def _default_hash_for_password(password: str) -> str:
        salt = b"nmp_sa_bootstrap"
        iterations = 600_000
        digest = pbkdf2_hmac("sha256", str(password or "").encode("utf-8"), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"

    @staticmethod
    def seed_default_device_types(conn, manager_cls) -> None:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT IGNORE INTO device_types(
                    code, label, icon, monitoring_enabled, config_backups_enabled, is_system, sort_order
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    ("switch", "Switch", "switch", 1, 1, 1, 10),
                    ("server", "Serveur", "server", 1, 0, 1, 20),
                ],
            )

            cursor.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'switch'")
            switch_fields_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'switch'")
            switch_actions_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_fields WHERE type_code = 'server'")
            server_fields_count = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM device_type_actions WHERE type_code = 'server'")
            server_actions_count = int(cursor.fetchone()[0] or 0)

            if switch_fields_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, show_in_table, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("switch", "name", "Nom", "text", 1, "", "", 1, 10),
                        ("switch", "ip", "IP", "ip", 1, "", "", 1, 20),
                        ("switch", "description", "Description", "text", 0, "", "", 0, 30),
                        ("switch", "type", "OS", "choice", 1, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, 0, 40),
                        ("switch", "action_double_click", "Action double-clic", "choice", 0, "web,ssh,teamviewer,remote_desktop", "", 0, 60),
                    ],
                )
            if switch_actions_count == 0:
                cursor.execute(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    ("switch", "web", "Ouvrir IP", "builtin", "web", manager_cls.ALL_OS_SCOPE, 10, 1),
                )
            if server_fields_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_fields(
                        type_code, field_key, label, field_kind, required, options, default_value, show_in_table, sort_order
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("server", "name", "Nom", "text", 1, "", "", 1, 10),
                        ("server", "ip", "IP", "ip", 1, "", "", 1, 20),
                        ("server", "description", "Description", "text", 0, "", "", 0, 30),
                        ("server", "type", "OS", "choice", 1, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, 0, 40),
                        ("server", "id_Teamviewer", "ID TeamViewer", "text", 0, "", "", 0, 50),
                        ("server", "action_double_click", "Action double-clic", "choice", 0, "ssh,web,teamviewer,remote_desktop", "", 0, 60),
                        ("server", "web_url", "URL interface web", "url", 0, "", "", 0, 70),
                        ("server", "ssh_user", "SSH user", "text", 0, "", "", 0, 80),
                    ],
                )
            if server_actions_count == 0:
                cursor.executemany(
                    """
                    INSERT INTO device_type_actions(
                        type_code, action_key, label, target_kind, target_value, os_scope, sort_order, is_default
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("server", "ssh", "SSH", "builtin", "ssh", manager_cls._format_os_scope(["linux", "firmware", "autre"]), 10, 0),
                        ("server", "web", "Web", "builtin", "web", manager_cls.ALL_OS_SCOPE, 20, 0),
                        ("server", "teamviewer", "TeamViewer", "builtin", "teamviewer", manager_cls._format_os_scope(["windows", "linux", "autre"]), 30, 0),
                        ("server", "remote_desktop", "Remote Desktop", "builtin", "remote_desktop", manager_cls._format_os_scope(["windows", "autre"]), 40, 1),
                    ],
                )
        conn.commit()

    @staticmethod
    def ensure_os_field_rows(conn, manager_cls) -> None:
        with conn.cursor() as cursor:
            cursor.execute("SELECT code FROM device_types ORDER BY sort_order, label")
            rows = cursor.fetchall()
            for (type_code,) in rows:
                code = str(type_code or "").strip().lower()
                if not code:
                    continue
                cursor.execute(
                    """
                    SELECT id, sort_order, options, default_value
                    FROM device_type_fields
                    WHERE type_code = %s AND field_key = 'type'
                    """,
                    (code,),
                )
                os_row = cursor.fetchone()
                if os_row is None:
                    cursor.execute(
                        """
                        SELECT sort_order
                        FROM device_type_fields
                        WHERE type_code = %s AND field_key = 'description'
                        """,
                        (code,),
                    )
                    desc_sort = cursor.fetchone()
                    sort_order = int(desc_sort[0]) + 10 if desc_sort is not None else 40
                    cursor.execute(
                        """
                        INSERT INTO device_type_fields(
                            type_code, field_key, label, field_kind, required, options, default_value, show_in_table, sort_order
                        ) VALUES (%s, 'type', 'OS', 'choice', 1, %s, %s, 0, %s)
                        """,
                        (code, manager_cls.OS_FIELD_OPTIONS, manager_cls.OS_FIELD_DEFAULT, sort_order),
                    )
                    continue
                raw_options = str(os_row[2] or "").strip()
                options_values = [part.strip() for part in raw_options.split(",") if part.strip()]
                if not options_values:
                    options_values = [part.strip() for part in str(manager_cls.OS_FIELD_OPTIONS).split(",") if part.strip()]
                normalized_options = ",".join(options_values) if options_values else str(manager_cls.OS_FIELD_OPTIONS)
                raw_default = str(os_row[3] or "").strip()
                normalized_default = raw_default if raw_default in options_values else (options_values[0] if options_values else str(manager_cls.OS_FIELD_DEFAULT))
                cursor.execute(
                    """
                    UPDATE device_type_fields
                    SET label = 'OS',
                        field_kind = 'choice',
                        required = 1,
                        options = %s,
                        default_value = %s
                    WHERE type_code = %s AND field_key = 'type'
                    """,
                    (normalized_options, normalized_default, code),
                )
        conn.commit()

    @staticmethod
    def ensure_action_os_scope_rows(conn, manager_cls) -> None:
        legacy_scope = {
            "ssh": manager_cls._format_os_scope(["linux", "firmware", "autre"]),
            "web": manager_cls._format_os_scope(["windows", "linux", "firmware", "autre"]),
            "teamviewer": manager_cls._format_os_scope(["windows", "linux", "autre"]),
            "remote_desktop": manager_cls._format_os_scope(["windows", "autre"]),
        }
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT type_code, action_key, os_scope
                FROM device_type_actions
                """
            )
            rows = cursor.fetchall()
            for type_code, action_key, os_scope in rows:
                if str(os_scope or "").strip():
                    continue
                key = str(action_key or "").strip().lower()
                scope = legacy_scope.get(key, manager_cls.ALL_OS_SCOPE)
                cursor.execute(
                    """
                    UPDATE device_type_actions
                    SET os_scope = %s
                    WHERE type_code = %s AND action_key = %s
                    """,
                    (scope, str(type_code), key),
                )
        conn.commit()
