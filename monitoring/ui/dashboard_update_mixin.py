from __future__ import annotations

import os
import subprocess
import threading
import shutil
from tkinter import Label, Toplevel, messagebox, ttk

from monitoring.config.settings import save_settings
from monitoring.utils.updater import download_update_asset, find_available_update


class DashboardUpdateMixin:
    def _open_update_settings_dialog(self) -> None:
        from monitoring.ui.dialogs.update_settings import UpdateSettingsDialog

        dlg = UpdateSettingsDialog(self.root, self.notification_settings)
        if dlg.result:
            self.notification_settings = dlg.result
            save_settings(self.notification_settings)
            if bool(getattr(self.notification_settings, "updates_enabled", False)):
                self._check_updates_now_interactive()

    def _check_updates_now_interactive(self) -> None:
        def worker() -> None:
            try:
                info = find_available_update(self.app_version, self.notification_settings)
            except Exception as exc:
                self.root.after(0, lambda: messagebox.showerror("Mise a jour", f"Verification impossible: {exc}"))
                return
            if info is None:
                self.root.after(0, lambda: messagebox.showinfo("Mise a jour", "Aucune mise a jour disponible."))
                return
            self.root.after(0, lambda: self._prompt_install_update(info))

        threading.Thread(target=worker, daemon=True, name="UpdateCheckManual").start()

    def _check_updates_on_startup(self) -> None:
        if not bool(getattr(self.notification_settings, "updates_enabled", True)):
            return

        def worker() -> None:
            try:
                info = find_available_update(self.app_version, self.notification_settings)
            except Exception as exc:
                self.logger.warning("Verification MAJ impossible: %s", exc)
                return
            if info is None:
                return
            self.root.after(0, lambda: self._prompt_install_update(info))

        threading.Thread(target=worker, daemon=True, name="UpdateCheck").start()

    def _prompt_install_update(self, info) -> None:
        msg = (
            f"Une nouvelle version est disponible: v{info.version}\n\n"
            f"Release: {info.release_name}\n\n"
            "Voulez-vous telecharger et installer la mise a jour maintenant ?"
        )
        if not messagebox.askyesno("Mise a jour disponible", msg):
            return
        self._show_update_progress("Telechargement de la mise a jour en cours...")

        def worker() -> None:
            try:
                setup_path = download_update_asset(info, self.notification_settings)
            except Exception as exc:
                self.root.after(
                    0,
                    lambda: (
                        self._close_update_progress(),
                        messagebox.showerror("Mise a jour", f"Telechargement impossible: {exc}"),
                    ),
                )
                return
            self.root.after(
                0,
                lambda: (
                    self._close_update_progress(),
                    self._run_installer_and_exit(setup_path),
                ),
            )

        threading.Thread(target=worker, daemon=True, name="UpdateDownload").start()

    def _show_update_progress(self, message: str) -> None:
        try:
            if getattr(self, "_update_progress_win", None) is not None:
                self._close_update_progress()
            progress_win = Toplevel(self.root)
            progress_win.title("Mise a jour")
            progress_win.transient(self.root)
            progress_win.grab_set()
            progress_win.resizable(False, False)
            progress_win.configure(bg=self.theme.colors["app_bg"])
            Label(
                progress_win,
                text=message,
                bg=self.theme.colors["app_bg"],
                fg=self.theme.colors["text_primary"],
            ).pack(padx=16, pady=(14, 8))
            bar = ttk.Progressbar(progress_win, mode="indeterminate", length=280)
            bar.pack(padx=16, pady=(0, 14))
            bar.start(12)
            self._update_progress_win = progress_win
            self._update_progress_bar = bar
            try:
                progress_win.update_idletasks()
                w = progress_win.winfo_width()
                h = progress_win.winfo_height()
                x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (w // 2)
                y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (h // 2)
                progress_win.geometry(f"+{max(0, x)}+{max(0, y)}")
            except Exception:
                pass
        except Exception:
            self._update_progress_win = None
            self._update_progress_bar = None

    def _close_update_progress(self) -> None:
        bar = getattr(self, "_update_progress_bar", None)
        win = getattr(self, "_update_progress_win", None)
        try:
            if bar is not None:
                bar.stop()
        except Exception:
            pass
        try:
            if win is not None and win.winfo_exists():
                win.grab_release()
                win.destroy()
        except Exception:
            pass
        self._update_progress_bar = None
        self._update_progress_win = None

    def _run_installer_and_exit(self, setup_path: str) -> None:
        try:
            pid = int(os.getpid())
            exe_path = str(setup_path).replace("'", "''")
            ps_script = (
                f"$pidToWait={pid}; "
                "while (Get-Process -Id $pidToWait -ErrorAction SilentlyContinue) "
                "{ Start-Sleep -Milliseconds 300 }; "
                f"Start-Process -FilePath '{exe_path}'"
            )
            creation_flags = 0
            creation_flags |= int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
            creation_flags |= int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
            ps_exe = shutil.which("powershell") or shutil.which("pwsh")
            if ps_exe:
                subprocess.Popen(
                    [
                        ps_exe,
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-Command",
                        ps_script,
                    ],
                    shell=False,
                    creationflags=creation_flags,
                )
            else:
                subprocess.Popen(["cmd", "/c", "start", "", setup_path], shell=False)
        except Exception as exc:
            messagebox.showerror("Mise a jour", f"Impossible de preparer l'installation: {exc}")
            return
        self._on_closing()
