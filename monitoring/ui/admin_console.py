from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from typing import Callable
from tkinter import BOTH, LEFT, RIGHT, TOP, X, Button, Frame, Label, StringVar, Tk, filedialog, messagebox, ttk

from monitoring.backend.app_backend import ApplicationBackend
from monitoring.config.settings import NotificationSettings
from monitoring.services.caddy_manager import CaddyManager
from monitoring.services.settings_service import SettingsService
from monitoring.services.web_server_manager import WebServerManager
from monitoring.storage.mariadb_manager import MariaDBFileManager
from monitoring.ui.base_window import BaseWindow
from monitoring.ui.dialogs.notification_settings import NotificationSettingsDialog
from monitoring.ui.dialogs.status_logs_viewer import StatusLogsViewer
from monitoring.ui.dialogs.technical_logs_viewer import TechnicalLogsViewer
from monitoring.ui.dialogs.web_server_settings import WebServerSettingsDialog
from monitoring.ui.theme_manager import resolve_theme
from monitoring.ui.theme_utils import bind_control_button_hover
from monitoring.utils.logger import log_with_timestamp
from monitoring.versioning import resolve_display_version


class AdminConsoleIHM(BaseWindow):
    """Console desktop legere: serveur web, notifications et journaux."""

    def __init__(
        self,
        root: Tk,
        *,
        manager: MariaDBFileManager,
        settings_service: SettingsService,
        backend_factory: Callable[[], ApplicationBackend],
    ) -> None:
        self.app_version = resolve_display_version()
        super().__init__(root, title=f"Console Admin Monitoring v{self.app_version}")

        self.manager = manager
        self.settings_service = settings_service
        self._backend_factory = backend_factory
        self._runtime_backend: ApplicationBackend | None = None
        self._backend_lock = threading.Lock()
        self.notification_settings: NotificationSettings = self.settings_service.get()
        self.theme = resolve_theme(str(getattr(self.notification_settings, "ui_theme", "light") or "light"))
        self.caddy_manager = CaddyManager()
        self.web_server_manager = WebServerManager(
            app_factory=self._build_asgi_app,
        )

        self._refresh_job: str | None = None
        self._web_action_running = False

        self.var_server_state = StringVar(value="-")
        self.var_server_url = StringVar(value="-")
        self.var_server_mode = StringVar(value="-")

        self.root.geometry("940x560")
        self.root.minsize(860, 500)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._build_ui()
        self.center_window()
        self._refresh_web_server_state()
        self._refresh_status_type_choices()
        self._maybe_sync_public_web_proxy()
        self._maybe_autostart_web_server()

    def _build_ui(self) -> None:
        c = self.theme.colors
        self.root.configure(bg=c["app_bg"])

        shell = Frame(self.root, bg=c["app_bg"])
        shell.pack(fill=BOTH, expand=True, padx=14, pady=14)

        header = Frame(shell, bg=c["app_bg"])
        header.pack(fill=X, side=TOP, pady=(0, 12))
        Label(
            header,
            text="Console admin desktop",
            bg=c["app_bg"],
            fg=c["text_primary"],
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        Label(
            header,
            text=(
                "Mode optimise ressources: pilotage du serveur web, notifications email et consultation des journaux."
            ),
            bg=c["app_bg"],
            fg=c["text_secondary"],
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        self._build_web_server_panel(shell)
        self._build_notifications_panel(shell)
        self._build_logs_panel(shell)

        footer = Frame(shell, bg=c["app_bg"])
        footer.pack(fill=X, side=TOP, pady=(12, 0))
        btn_quit = Button(footer, text="Fermer", command=self._on_closing)
        btn_quit.pack(side=RIGHT)
        bind_control_button_hover(btn_quit, c)

    def _build_web_server_panel(self, parent: Frame) -> None:
        c = self.theme.colors
        panel = Frame(
            parent,
            bg=c["panel_bg"],
            bd=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
        )
        panel.pack(fill=X, side=TOP, pady=(0, 10))

        Label(
            panel,
            text="Serveur web",
            bg=c["panel_bg"],
            fg=c["text_primary"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 2))

        info = Frame(panel, bg=c["panel_bg"])
        info.pack(fill=X, padx=10, pady=(0, 8))
        Label(info, text="Etat:", bg=c["panel_bg"], fg=c["text_secondary"], width=10, anchor="w").pack(side=LEFT)
        Label(info, textvariable=self.var_server_state, bg=c["panel_bg"], fg=c["text_primary"], anchor="w").pack(side=LEFT)
        Label(info, text="URL:", bg=c["panel_bg"], fg=c["text_secondary"], width=8, anchor="e").pack(side=LEFT, padx=(24, 6))
        Label(info, textvariable=self.var_server_url, bg=c["panel_bg"], fg=c["text_primary"], anchor="w").pack(side=LEFT)
        Label(info, text="Mode:", bg=c["panel_bg"], fg=c["text_secondary"], width=8, anchor="e").pack(side=LEFT, padx=(24, 6))
        Label(info, textvariable=self.var_server_mode, bg=c["panel_bg"], fg=c["text_primary"], anchor="w").pack(side=LEFT)

        actions = Frame(panel, bg=c["panel_bg"])
        actions.pack(fill=X, padx=10, pady=(0, 10))
        self.btn_web_toggle = Button(actions, text="Demarrer / Arreter", command=self._toggle_web_server_interactive)
        self.btn_web_toggle.pack(side=LEFT, padx=(0, 8))
        self.btn_web_restart = Button(actions, text="Redemarrer", command=self._restart_web_server_interactive)
        self.btn_web_restart.pack(side=LEFT, padx=(0, 8))
        self.btn_web_open = Button(actions, text="Ouvrir interface web", command=self._open_web_ui_in_browser)
        self.btn_web_open.pack(side=LEFT, padx=(0, 8))
        self.btn_web_settings = Button(actions, text="Parametres...", command=self._open_web_server_dialog)
        self.btn_web_settings.pack(side=LEFT, padx=(0, 8))
        self.btn_web_cert = Button(actions, text="Exporter certificat HTTPS...", command=self._export_https_root_certificate)
        self.btn_web_cert.pack(side=LEFT, padx=(0, 8))

        for btn in (
            self.btn_web_toggle,
            self.btn_web_restart,
            self.btn_web_open,
            self.btn_web_settings,
            self.btn_web_cert,
        ):
            bind_control_button_hover(btn, c)

    def _build_notifications_panel(self, parent: Frame) -> None:
        c = self.theme.colors
        panel = Frame(
            parent,
            bg=c["panel_bg"],
            bd=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
        )
        panel.pack(fill=X, side=TOP, pady=(0, 10))

        Label(
            panel,
            text="Notifications",
            bg=c["panel_bg"],
            fg=c["text_primary"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 2))
        Label(
            panel,
            text="Configuration SMTP, destinataires et popup de statut.",
            bg=c["panel_bg"],
            fg=c["text_secondary"],
        ).pack(anchor="w", padx=10, pady=(0, 8))

        actions = Frame(panel, bg=c["panel_bg"])
        actions.pack(fill=X, padx=10, pady=(0, 10))
        btn_notif = Button(actions, text="Parametres notifications...", command=self._open_notification_dialog)
        btn_notif.pack(side=LEFT)
        bind_control_button_hover(btn_notif, c)

    def _build_logs_panel(self, parent: Frame) -> None:
        c = self.theme.colors
        panel = Frame(
            parent,
            bg=c["panel_bg"],
            bd=1,
            relief="flat",
            highlightthickness=1,
            highlightbackground=c["placeholder_border"],
        )
        panel.pack(fill=X, side=TOP)

        Label(
            panel,
            text="Journaux",
            bg=c["panel_bg"],
            fg=c["text_primary"],
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w", padx=10, pady=(10, 2))
        Label(
            panel,
            text="Consultation des logs techniques et des changements de statut.",
            bg=c["panel_bg"],
            fg=c["text_secondary"],
        ).pack(anchor="w", padx=10, pady=(0, 8))

        actions = Frame(panel, bg=c["panel_bg"])
        actions.pack(fill=X, padx=10, pady=(0, 10))
        btn_tech = Button(actions, text="Logs techniques...", command=self._open_technical_logs)
        btn_tech.pack(side=LEFT, padx=(0, 8))
        btn_status_global = Button(actions, text="Journal statut global...", command=self._open_global_status_logs)
        btn_status_global.pack(side=LEFT, padx=(0, 8))
        for btn in (btn_tech, btn_status_global):
            bind_control_button_hover(btn, c)

        type_row = Frame(actions, bg=c["panel_bg"])
        type_row.pack(side=LEFT, padx=(10, 0))
        Label(type_row, text="Type:", bg=c["panel_bg"], fg=c["text_secondary"]).pack(side=LEFT, padx=(0, 6))
        self.type_combo = ttk.Combobox(type_row, state="readonly", width=24, values=[])
        self.type_combo.pack(side=LEFT)
        btn_status_type = Button(type_row, text="Journal type...", command=self._open_status_logs_for_selected_type)
        btn_status_type.pack(side=LEFT, padx=(8, 0))
        bind_control_button_hover(btn_status_type, c)

    def _load_settings(self) -> NotificationSettings:
        return self.settings_service.get()

    def _save_settings(self) -> NotificationSettings:
        return self.settings_service.save(self.notification_settings)

    def _web_server_host(self) -> str:
        return str(getattr(self.notification_settings, "web_server_host", "127.0.0.1") or "127.0.0.1").strip()

    def _web_server_port(self) -> int:
        return max(1, int(getattr(self.notification_settings, "web_server_port", 8000) or 8000))

    def _web_server_public_url(self) -> str:
        return str(getattr(self.notification_settings, "web_server_public_url", "") or "").strip().rstrip("/")

    def _preferred_web_server_url(self) -> str:
        public_url = self._web_server_public_url()
        if bool(getattr(self.notification_settings, "web_server_use_public_url", False)) and public_url:
            return f"{public_url}/"
        return f"http://{self._web_server_host()}:{self._web_server_port()}/"

    def _is_web_server_busy(self) -> bool:
        return bool(self._web_action_running)

    def _set_web_server_busy(self, busy: bool) -> None:
        self._web_action_running = bool(busy)
        state = "disabled" if busy else "normal"
        for btn in (
            self.btn_web_toggle,
            self.btn_web_restart,
            self.btn_web_open,
            self.btn_web_settings,
            self.btn_web_cert,
        ):
            try:
                btn.configure(state=state)
            except Exception:
                continue
        if busy:
            self.var_server_state.set("Operation...")
        else:
            self._refresh_web_server_state()

    def _refresh_web_server_state(self) -> None:
        state = self.web_server_manager.state()
        self.var_server_state.set("Actif" if state.running else "Arrete")
        self.var_server_url.set(state.url)
        mode = "Public" if bool(getattr(self.notification_settings, "web_server_use_public_url", False)) else "Local"
        self.var_server_mode.set(mode)
        if self._is_web_server_busy():
            return
        self.btn_web_restart.configure(state="normal" if state.running else "disabled")
        self.btn_web_toggle.configure(text="Arreter" if state.running else "Demarrer")
        if self._refresh_job is not None:
            try:
                self.root.after_cancel(self._refresh_job)
            except Exception:
                pass
        self._refresh_job = self.root.after(1200, self._refresh_web_server_state)

    def _refresh_status_type_choices(self) -> None:
        labels: list[str] = []
        mapping: dict[str, str] = {}
        rows = sorted(
            list(self.manager.list_device_types()),
            key=lambda row: (
                int(row.get("sort_order", 0) or 0),
                str(row.get("label", row.get("code", ""))).lower(),
            ),
        )
        for row in rows:
            if not bool(row.get("monitoring_enabled", True)):
                continue
            dtype = str(row.get("code", "")).strip()
            if not dtype:
                continue
            label = str(row.get("label", dtype)).strip() or str(dtype)
            display = f"{label} ({dtype})"
            labels.append(display)
            mapping[display] = str(dtype)
        self._status_type_mapping = mapping
        self.type_combo.configure(values=labels)
        if labels:
            self.type_combo.set(labels[0])
        else:
            self.type_combo.set("")

    def _on_closing(self) -> None:
        try:
            if self._refresh_job is not None:
                try:
                    self.root.after_cancel(self._refresh_job)
                except Exception:
                    pass
                self._refresh_job = None
            self.web_server_manager.stop()
            self._stop_public_web_proxy_on_shutdown()
            backend = self._runtime_backend
            if backend is not None:
                backend.shutdown()
        finally:
            self.root.destroy()

    def _open_notification_dialog(self) -> None:
        self.notification_settings = self._load_settings()
        dlg = NotificationSettingsDialog(self.root, self.notification_settings)
        if dlg.result is None:
            return
        self.notification_settings = dlg.result
        self._save_settings()

    def _open_global_status_logs(self) -> None:
        StatusLogsViewer(
            self.root,
            title="Journal global des changements de statut",
            manager=self.manager,
        )

    def _open_status_logs_for_selected_type(self) -> None:
        selected = str(self.type_combo.get() or "").strip()
        if not selected:
            messagebox.showinfo("Journaux", "Aucun type disponible.")
            return
        dtype = str(self._status_type_mapping.get(selected, "")).strip()
        if not dtype:
            messagebox.showerror("Journaux", "Type invalide.")
            return
        StatusLogsViewer(
            self.root,
            title=f"Journal des changements - {dtype}",
            dtype=dtype,
            manager=self.manager,
        )

    def _open_technical_logs(self) -> None:
        TechnicalLogsViewer(self.root)

    def _open_web_server_dialog(self) -> None:
        self.notification_settings = self._load_settings()
        WebServerSettingsDialog(
            self.root,
            host=self._web_server_host(),
            port=self._web_server_port(),
            autostart=bool(getattr(self.notification_settings, "web_server_autostart", False)),
            public_url=self._web_server_public_url(),
            use_public_url=bool(getattr(self.notification_settings, "web_server_use_public_url", False)),
            state_provider=self.web_server_manager.state,
            on_save=self._save_web_server_settings,
            on_toggle=self._toggle_web_server_dialog_action,
            on_restart=self._restart_web_server_dialog_action,
            on_open_browser=self._open_web_ui_for_host_port,
        )

    def _save_web_server_settings(
        self,
        host: str,
        port: int,
        autostart: bool,
        public_url: str = "",
        use_public_url: bool = False,
    ) -> None:
        self.notification_settings.web_server_host = str(host or "127.0.0.1").strip() or "127.0.0.1"
        self.notification_settings.web_server_port = max(1, int(port or 8000))
        self.notification_settings.web_server_autostart = bool(autostart)
        self.notification_settings.web_server_public_url = str(public_url or "").strip().rstrip("/")
        self.notification_settings.web_server_use_public_url = bool(use_public_url)
        self._save_settings()
        self._maybe_sync_public_web_proxy()
        self._refresh_web_server_state()

    def _run_web_server_operation(
        self,
        operation,
        *,
        on_success=None,
        show_feedback: bool = False,
        success_message: str = "",
    ) -> None:
        if self._is_web_server_busy():
            return
        self._set_web_server_busy(True)

        def schedule_ui_call(callback) -> None:
            try:
                if bool(self.root.winfo_exists()):
                    self.root.after(0, callback)
            except Exception:
                pass

        def worker() -> None:
            try:
                state = operation()
                schedule_ui_call(lambda: handle_success(state))
            except Exception as exc:
                schedule_ui_call(lambda e=exc: handle_error(e))

        def handle_success(state) -> None:
            self._set_web_server_busy(False)
            if callable(on_success):
                on_success(state)
            if show_feedback and success_message:
                messagebox.showinfo("Serveur web", f"{success_message}\n{state.url}")

        def handle_error(exc: Exception) -> None:
            self._set_web_server_busy(False)
            messagebox.showerror("Serveur web", f"Operation impossible: {exc}")

        threading.Thread(target=worker, daemon=True, name="AdminConsoleWebAction").start()

    def _toggle_web_server_interactive(self) -> None:
        state = self.web_server_manager.state()
        if state.running:
            self._run_web_server_operation(
                self.web_server_manager.stop,
                show_feedback=True,
                success_message="Serveur web arrete.",
            )
            return
        self._run_web_server_operation(
            lambda: self.web_server_manager.start(
                host=self._web_server_host(),
                port=self._web_server_port(),
                open_browser=False,
            ),
            show_feedback=True,
            success_message="Serveur web actif sur:",
        )

    def _restart_web_server_interactive(self) -> None:
        self._run_web_server_operation(
            lambda: self.web_server_manager.restart(
                host=self._web_server_host(),
                port=self._web_server_port(),
                open_browser=False,
            ),
            show_feedback=True,
            success_message="Serveur web redemarre sur:",
        )

    def _open_web_ui_in_browser(self) -> None:
        if self.web_server_manager.state().running:
            try:
                webbrowser.open(self._preferred_web_server_url())
            except Exception as exc:
                messagebox.showerror("Serveur web", f"Impossible d'ouvrir le navigateur: {exc}")
            return

        def open_browser_after_start(_state) -> None:
            try:
                webbrowser.open(self._preferred_web_server_url())
            except Exception as exc:
                messagebox.showerror("Serveur web", f"Impossible d'ouvrir le navigateur: {exc}")

        self._run_web_server_operation(
            lambda: self.web_server_manager.start(
                host=self._web_server_host(),
                port=self._web_server_port(),
                open_browser=False,
            ),
            on_success=open_browser_after_start,
        )

    def _open_web_ui_for_host_port(self, host: str, port: int) -> None:
        self._save_web_server_settings(
            host,
            port,
            bool(getattr(self.notification_settings, "web_server_autostart", False)),
            self._web_server_public_url(),
            bool(getattr(self.notification_settings, "web_server_use_public_url", False)),
        )
        if self.web_server_manager.state().running:
            try:
                webbrowser.open(self._preferred_web_server_url())
            except Exception as exc:
                messagebox.showerror("Serveur web", f"Impossible d'ouvrir le navigateur: {exc}")
            return
        self._run_web_server_operation(
            lambda: self.web_server_manager.start(
                host=self._web_server_host(),
                port=self._web_server_port(),
                open_browser=False,
            ),
            on_success=lambda _state: webbrowser.open(self._preferred_web_server_url()),
        )

    def _toggle_web_server_dialog_action(self, host: str, port: int) -> None:
        state = self.web_server_manager.state()
        if state.running and (state.host != str(host) or state.port != int(port)):
            self._run_web_server_operation(
                lambda: self.web_server_manager.restart(
                    host=str(host),
                    port=int(port),
                    open_browser=False,
                ),
            )
            return
        if state.running:
            self._run_web_server_operation(self.web_server_manager.stop)
            return
        self._run_web_server_operation(
            lambda: self.web_server_manager.start(
                host=str(host),
                port=int(port),
                open_browser=False,
            ),
        )

    def _restart_web_server_dialog_action(self, host: str, port: int) -> None:
        self._run_web_server_operation(
            lambda: self.web_server_manager.restart(
                host=str(host),
                port=int(port),
                open_browser=False,
            ),
        )

    def _maybe_autostart_web_server(self) -> None:
        if bool(getattr(self.notification_settings, "web_server_autostart", False)):
            self.root.after(
                250,
                lambda: self._run_web_server_operation(
                    lambda: self.web_server_manager.start(
                        host=self._web_server_host(),
                        port=self._web_server_port(),
                        open_browser=False,
                    ),
                ),
            )

    def _maybe_sync_public_web_proxy(self) -> None:
        if not bool(getattr(self.notification_settings, "web_server_use_public_url", False)):
            return
        if not self._web_server_public_url():
            return

        def worker() -> None:
            try:
                self.caddy_manager.sync_from_settings(self.notification_settings)
            except PermissionError as exc:
                log_with_timestamp(f"Sync proxy public ignoree (droits insuffisants): {exc}", level="WARNING")
            except Exception as exc:
                try:
                    if bool(self.root.winfo_exists()):
                        self.root.after(
                            0,
                            lambda e=exc: messagebox.showerror(
                                "Proxy HTTPS",
                                f"Impossible de synchroniser le proxy public: {e}",
                            ),
                        )
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True, name="AdminConsoleCaddySync").start()

    def _stop_public_web_proxy_on_shutdown(self) -> None:
        try:
            self.caddy_manager.stop_service()
        except Exception as exc:
            log_with_timestamp(f"Arret proxy public ignore (erreur): {exc}", level="WARNING")

    def _export_https_root_certificate(self) -> None:
        default_name = "monitoring-mvl-root.crt"
        target = filedialog.asksaveasfilename(
            parent=self.root,
            title="Exporter le certificat HTTPS",
            defaultextension=".crt",
            initialfile=default_name,
            filetypes=[("Certificat", "*.crt"), ("Tous les fichiers", "*.*")],
        )
        if not target:
            return
        try:
            exported = self.caddy_manager.export_root_certificate(Path(target))
            messagebox.showinfo(
                "Serveur web",
                "Certificat exporte.\n\n"
                f"Fichier: {exported}\n\n"
                "Importez ce certificat sur les postes autorises dans le magasin 'Trusted Root'.",
            )
        except Exception as exc:
            messagebox.showerror("Serveur web", f"Impossible d'exporter le certificat HTTPS: {exc}")

    def _ensure_runtime_backend(self) -> ApplicationBackend:
        with self._backend_lock:
            if self._runtime_backend is None:
                self._runtime_backend = self._backend_factory()
            return self._runtime_backend

    def _build_asgi_app(self):
        from monitoring.api.app import create_app

        return create_app(backend=self._ensure_runtime_backend(), stop_runtime_on_shutdown=False)
