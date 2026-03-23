from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

from monitoring.utils.logger import log_with_timestamp


class DashboardWebServerMixin:
    """Web server and public proxy actions for the dashboard."""

    def _web_server_url(self) -> str:
        return f"http://{self._web_server_host()}:{self._web_server_port()}/"

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
        return self._web_server_url()

    def _maybe_autostart_web_server(self) -> None:
        if bool(getattr(self.notification_settings, "web_server_autostart", False)):
            self.root.after(300, self._start_web_server_silent)

    def _maybe_sync_public_web_proxy(self) -> None:
        if not bool(getattr(self.notification_settings, "web_server_use_public_url", False)):
            return
        if not self._web_server_public_url():
            return

        def worker() -> None:
            try:
                self.caddy_manager.sync_from_settings(self.notification_settings)
            except PermissionError as exc:
                log_with_timestamp(
                    f"Sync proxy public ignoree (droits insuffisants): {exc}",
                    level="WARNING",
                )
            except Exception as exc:
                self.root.after(
                    0,
                    lambda e=exc: messagebox.showerror(
                        "Proxy HTTPS",
                        f"Impossible de synchroniser le proxy public: {e}",
                    ),
                )

        threading.Thread(target=worker, daemon=True, name="CaddySync").start()

    def _open_web_server_dialog(self) -> None:
        from monitoring.ui.dialogs.web_server_settings import WebServerSettingsDialog

        WebServerSettingsDialog(
            self.root,
            host=str(getattr(self.notification_settings, "web_server_host", "127.0.0.1")),
            port=int(getattr(self.notification_settings, "web_server_port", 8000)),
            autostart=bool(getattr(self.notification_settings, "web_server_autostart", False)),
            public_url=self._web_server_public_url(),
            use_public_url=bool(getattr(self.notification_settings, "web_server_use_public_url", False)),
            state_provider=self.web_server_manager.state,
            on_save=self._save_web_server_settings,
            on_toggle=self._toggle_web_server_dialog_action,
            on_restart=self._restart_web_server_dialog_action,
            on_open_browser=self._open_web_ui_for_host_port,
        )

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

    def _save_web_server_settings(
        self,
        host: str,
        port: int,
        autostart: bool,
        public_url: str = "",
        use_public_url: bool = False,
    ) -> None:
        self.notification_settings.web_server_host = str(host)
        self.notification_settings.web_server_port = int(port)
        self.notification_settings.web_server_autostart = bool(autostart)
        self.notification_settings.web_server_public_url = str(public_url or "").strip().rstrip("/")
        self.notification_settings.web_server_use_public_url = bool(use_public_url)
        self._save_settings()
        self.caddy_manager.sync_from_settings(self.notification_settings)
        self.update_display()

    def _web_server_start_operation(self, *, host: str | None = None, port: int | None = None, open_browser: bool) -> object:
        return self.web_server_manager.start(
            host=str(host or self._web_server_host()),
            port=int(port or self._web_server_port()),
            open_browser=open_browser,
        )

    def _web_server_restart_operation(self, *, host: str | None = None, port: int | None = None, open_browser: bool = False) -> object:
        return self.web_server_manager.restart(
            host=str(host or self._web_server_host()),
            port=int(port or self._web_server_port()),
            open_browser=open_browser,
        )

    def _start_web_server(self, *, show_feedback: bool, open_browser: bool = False) -> None:
        self._run_web_server_operation(
            lambda: self._web_server_start_operation(open_browser=open_browser),
            success_message="Serveur web actif sur:",
            show_feedback=show_feedback,
        )

    def _start_web_server_silent(self) -> None:
        self._start_web_server(show_feedback=False)

    def _start_web_server_interactive(self) -> None:
        self._start_web_server(show_feedback=True)

    def _stop_web_server_interactive(self) -> None:
        self._run_web_server_operation(
            self.web_server_manager.stop,
            success_message="Serveur web arrete.\nURL:",
            show_feedback=True,
        )

    def _restart_web_server_interactive(self) -> None:
        self._run_web_server_operation(
            lambda: self._web_server_restart_operation(),
            success_message="Serveur web redemarre sur:",
            show_feedback=True,
            transient_state="Redemarrage...",
        )

    def _open_web_ui_in_browser(self) -> None:
        if not self.web_server_manager.state().running:
            self._start_web_server(show_feedback=False)
        try:
            webbrowser.open(self._preferred_web_server_url())
        except Exception as exc:
            messagebox.showerror("Serveur web", f"Impossible d'ouvrir le navigateur: {exc}")

    def _open_web_ui_for_host_port(self, host: str, port: int) -> None:
        self._save_web_server_settings(
            host,
            port,
            bool(getattr(self.notification_settings, "web_server_autostart", False)),
            self._web_server_public_url(),
            bool(getattr(self.notification_settings, "web_server_use_public_url", False)),
        )
        if not self.web_server_manager.state().running:
            self._run_web_server_operation(
                lambda: self._web_server_start_operation(host=str(host), port=int(port), open_browser=True),
                show_feedback=False,
            )
            return
        webbrowser.open(self._preferred_web_server_url())

    def _toggle_web_server_dialog_action(self, host: str, port: int) -> None:
        state = self.web_server_manager.state()
        if state.running and (state.host != str(host) or state.port != int(port)):
            self._run_web_server_operation(
                lambda: self._web_server_restart_operation(host=str(host), port=int(port)),
                show_feedback=False,
            )
            return
        if state.running:
            self._run_web_server_operation(self.web_server_manager.stop, show_feedback=False)
            return
        self._run_web_server_operation(
            lambda: self._web_server_start_operation(host=str(host), port=int(port), open_browser=False),
            show_feedback=False,
        )

    def _restart_web_server_dialog_action(self, host: str, port: int) -> None:
        self._run_web_server_operation(
            lambda: self._web_server_restart_operation(host=str(host), port=int(port)),
            show_feedback=False,
            transient_state="Redemarrage...",
        )

    def _toggle_web_server_from_dashboard(self) -> None:
        state = self.web_server_manager.state()
        if state.running:
            self._run_web_server_operation(self.web_server_manager.stop, show_feedback=False)
        else:
            self._run_web_server_operation(
                lambda: self._web_server_start_operation(open_browser=False),
                show_feedback=False,
            )

    def _play_web_server_from_dashboard(self) -> None:
        state = self.web_server_manager.state()
        if state.running:
            self._run_web_server_operation(
                lambda: self._web_server_restart_operation(open_browser=False),
                show_feedback=False,
                transient_state="Redemarrage...",
            )
            return
        self._run_web_server_operation(
            lambda: self._web_server_start_operation(open_browser=False),
            show_feedback=False,
        )

    def _stop_web_server_from_dashboard(self) -> None:
        self._run_web_server_operation(self.web_server_manager.stop, show_feedback=False)

    def _run_web_server_operation(
        self,
        operation,
        *,
        success_message: str | None = None,
        show_feedback: bool,
        transient_state: str | None = None,
    ) -> None:
        if transient_state:
            setattr(self, "_web_server_card_transient_state", str(transient_state))
            self.update_display()

        def worker() -> None:
            try:
                state = operation()
                self.root.after(0, lambda: self._on_web_server_operation_success(state, success_message, show_feedback))
            except Exception as exc:
                self.root.after(0, lambda e=exc: self._on_web_server_operation_error(e, show_feedback))

        threading.Thread(target=worker, daemon=True, name="WebServerAction").start()

    def _on_web_server_operation_success(self, state, success_message: str | None, show_feedback: bool) -> None:
        setattr(self, "_web_server_card_transient_state", "")
        self.update_display()
        if show_feedback and success_message:
            public_url = self._web_server_public_url()
            if bool(getattr(self.notification_settings, "web_server_use_public_url", False)) and public_url:
                messagebox.showinfo(
                    "Serveur web",
                    f"{success_message}\nURL publique: {public_url}/\nBackend local: {state.url}",
                )
            else:
                messagebox.showinfo("Serveur web", f"{success_message}\n{state.url}")

    def _on_web_server_operation_error(self, exc: Exception, show_feedback: bool) -> None:
        setattr(self, "_web_server_card_transient_state", "")
        self.update_display()
        del show_feedback  # unused, kept for API compatibility
        messagebox.showerror("Serveur web", f"Operation impossible: {exc}")
