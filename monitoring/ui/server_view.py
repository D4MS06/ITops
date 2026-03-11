# src/monitoring/ui/server_view.py

from __future__ import annotations

import logging
import shutil
import subprocess
import webbrowser
from tkinter import Frame, Menu, messagebox, simpledialog

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.storage.sqlite_manager import SQLiteFileManager
from monitoring.ui.device_list_view import DeviceListView
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.utils.action_compat import action_allows_os

LOGGER = logging.getLogger(__name__)


class ServerIHM(DeviceListView):
    """IHM de monitoring des serveurs."""

    device_type = "server"
    columns = ("name", "ip", "desc")
    headings = {"name": "Nom", "ip": "IP", "desc": "Description"}
    tag_configs: dict[str, dict] = {}

    def __init__(
        self,
        parent: Frame,
        *,
        model: DevicesModel | None = None,
        controller: AppController | None = None,
    ) -> None:
        self._mgr = model.manager if model is not None else SQLiteFileManager()
        super().__init__(parent, model=model, controller=controller)
        self.update_display()

    def _on_add(self) -> None:
        dlg = DeviceForm(self.parent, title="Ajouter un serveur", default_type="server")
        if dlg.result is None:
            return
        d = dlg.result
        success = self.model.add_device(
            "server",
            d["name"],
            d["ip"],
            d["desc"],
            id_Teamviewer=d.get("tv_id", ""),
            device_subtype=d.get("subtype", ""),
            action_double_click=d.get("action_double_click", ""),
            web_url=d.get("web_url", ""),
            ssh_user=d.get("ssh_user", ""),
            custom_data=d.get("custom_data", {}),
            notify=d.get("notify", True),
        )
        if not success:
            messagebox.showwarning("Duplication", "IP deja utilisee.")
        self.refresh_paused = False
        self.controller.refresh_views()

    def _on_edit(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Modifier", "Selectionnez un serveur.")
            return
        did = sel[0]
        dev = self.model.device_data["server"][did]
        initial = {
            "name": dev.name,
            "ip": dev.ip,
            "desc": dev.description,
            "subtype": getattr(dev, "type", ""),
            "tv_id": getattr(dev, "id_Teamviewer", ""),
            "action_double_click": getattr(dev, "action_double_click", ""),
            "web_url": getattr(dev, "web_url", ""),
            "ssh_user": getattr(dev, "ssh_user", ""),
            "notify": self.model.notify_flags["server"].get(did, True),
            "custom_data": self.model.extract_custom_data(dev),
        }
        dlg = DeviceForm(
            self.parent,
            title="Modifier Serveur",
            default_type="server",
            initial=initial,
        )
        if dlg.result is None:
            return
        d = dlg.result
        ok = self.model.update_device(
            "server",
            did,
            new_name=d["name"],
            new_ip=d["ip"],
            new_description=d["desc"],
            id_Teamviewer=d.get("tv_id", ""),
            device_subtype=d.get("subtype", ""),
            action_double_click=d.get("action_double_click", ""),
            web_url=d.get("web_url", ""),
            ssh_user=d.get("ssh_user", ""),
            custom_data=d.get("custom_data", {}),
            notify=d.get("notify", True),
        )
        if not ok:
            messagebox.showerror("Erreur", "Echec de la mise a jour.")
        self.refresh_paused = False
        self.controller.refresh_views()

    def _on_delete(self) -> None:
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Supprimer", "Selectionnez un serveur.")
            return
        if messagebox.askyesno("Confirmation", "Supprimer ce serveur ?"):
            self.model.delete_device("server", sel[0])
            self.refresh_paused = False
            self.controller.refresh_views()

    def _selected_server(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.model.device_data["server"].get(sel[0])

    def _open_context_ssh(self) -> None:
        dev = self._selected_server()
        if not dev:
            return
        try:
            ip = str(dev.ip).strip()
            ssh_user = str(getattr(dev, "ssh_user", "")).strip()
            if not ssh_user:
                ssh_user = simpledialog.askstring(
                    "Connexion SSH",
                    f"Login SSH pour {ip} :",
                    parent=self.parent,
                )
                ssh_user = (ssh_user or "").strip()
                if not ssh_user:
                    return
            self._open_ssh(ip, ssh_user)
        except Exception as exc:
            LOGGER.exception("Erreur ouverture SSH serveur : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir SSH pour {dev.ip}")

    def _open_context_web(self) -> None:
        dev = self._selected_server()
        if not dev:
            return
        try:
            subtype = str(getattr(dev, "type", "")).strip().lower()
            ip = str(getattr(dev, "ip", "")).strip()
            web_url = str(getattr(dev, "web_url", "")).strip()
            if subtype == "dsm":
                webbrowser.open(f"http://{ip}:5000")
            elif web_url:
                webbrowser.open(web_url)
        except Exception as exc:
            LOGGER.exception("Erreur ouverture WEB serveur : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'interface pour {dev.ip}")

    def _open_context_teamviewer(self) -> None:
        dev = self._selected_server()
        if not dev:
            return
        try:
            tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
            if tv_id:
                webbrowser.open(f"https://start.teamviewer.com/{tv_id}")
        except Exception as exc:
            LOGGER.exception("Erreur ouverture TeamViewer : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir TeamViewer pour {dev.ip}")

    def _open_context_rdp(self) -> None:
        dev = self._selected_server()
        if not dev:
            return
        try:
            ip = str(getattr(dev, "ip", "")).strip()
            if ip:
                subprocess.Popen(["mstsc", f"/v:{ip}"])
        except Exception as exc:
            LOGGER.exception("Erreur ouverture Remote Desktop : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir Remote Desktop pour {dev.ip}")

    def _build_context_menu(self) -> Menu:
        menu = super()._build_context_menu()

        dev = self._selected_server()
        if dev:
            self._add_network_tools_submenu(
                menu,
                str(getattr(dev, "ip", "")).strip(),
                at_index=0,
            )
            menu.insert_separator(1)
            self._append_dynamic_actions(menu, dev)
        return menu

    def _append_dynamic_actions(self, menu: Menu, dev) -> None:
        actions = self._mgr.list_type_actions("server")
        if not actions:
            return
        visible_actions = []
        for action in actions:
            if not action_allows_os(str(action.get("os_scope", "")), str(getattr(dev, "type", ""))):
                continue
            visible_actions.append(action)
        if not visible_actions:
            return
        menu.add_separator()
        for action in visible_actions:
            label = str(action.get("label", "")).strip() or str(action.get("action_key", "")).strip()
            target_kind = str(action.get("target_kind", "")).strip().lower()
            builtin = str(action.get("target_value", "")).strip().lower() or str(action.get("action_key", "")).strip().lower()
            state = "normal" if target_kind == "builtin" and self._can_run_builtin(dev, builtin) else "disabled"
            menu.add_command(
                label=label,
                state=state,
                command=lambda b=builtin, d=dev: self._run_builtin_action(d, b),
            )

    @staticmethod
    def _can_run_builtin(dev, builtin: str) -> bool:
        ip = str(getattr(dev, "ip", "")).strip()
        tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
        if builtin == "teamviewer":
            return bool(tv_id)
        if builtin in {"web", "ssh", "remote_desktop"}:
            return bool(ip)
        return False

    def _run_builtin_action(self, dev, builtin: str) -> None:
        ip = str(getattr(dev, "ip", "")).strip()
        subtype = str(getattr(dev, "type", "")).strip().lower()
        tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
        web_url = str(getattr(dev, "web_url", "")).strip()
        ssh_user = str(getattr(dev, "ssh_user", "")).strip()
        if builtin == "teamviewer":
            if tv_id:
                webbrowser.open(f"https://start.teamviewer.com/{tv_id}")
            return
        if builtin == "remote_desktop":
            subprocess.Popen(["mstsc", f"/v:{ip}"])
            return
        if builtin == "ssh":
            self._open_ssh(ip, ssh_user)
            return
        if web_url:
            webbrowser.open(web_url)
        elif subtype == "dsm":
            webbrowser.open(f"http://{ip}:5000")
        else:
            webbrowser.open(f"http://{ip}")

    @staticmethod
    def _default_action(device_subtype: str, tv_id: str) -> str:
        subtype = (device_subtype or "").strip().lower()
        if subtype == "windows":
            return "teamviewer" if tv_id else "remote_desktop"
        if subtype == "linux":
            return "ssh"
        return "web"

    @staticmethod
    def _fallback_web_url(ip: str, device_subtype: str) -> str:
        subtype = (device_subtype or "").strip().lower()
        if subtype == "dsm":
            return f"http://{ip}:5000"
        return f"http://{ip}"

    @staticmethod
    def _open_ssh(ip: str, ssh_user: str) -> None:
        if ssh_user:
            target = f"{ssh_user}@{ip}"
            if shutil.which("wt"):
                subprocess.Popen(["wt", "ssh", target])
                return
            subprocess.Popen(["cmd", "/c", "start", "ssh", target])
            return

        subprocess.Popen(
            [
                "cmd.exe",
                "/k",
                f"set /p u=SSH login: && ssh %u%@{ip}",
            ]
        )

    def _on_double_click(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        dev = self.model.device_data["server"].get(sel[0])
        if not dev:
            return

        try:
            subtype = str(getattr(dev, "type", "")).strip().lower()
            ip = str(getattr(dev, "ip", "")).strip()
            tv_id = str(getattr(dev, "id_Teamviewer", "")).strip()
            action = str(getattr(dev, "action_double_click", "")).strip().lower()
            web_url = str(getattr(dev, "web_url", "")).strip()
            ssh_user = str(getattr(dev, "ssh_user", "")).strip()

            allowed_action_keys = [
                str(a.get("action_key", "")).strip().lower()
                for a in self._mgr.list_type_actions("server")
                if action_allows_os(str(a.get("os_scope", "")), subtype)
            ]
            if action and action not in allowed_action_keys:
                action = ""
            if not action:
                action = allowed_action_keys[0] if allowed_action_keys else self._default_action(subtype, tv_id)

            if action == "teamviewer":
                if tv_id:
                    webbrowser.open(f"https://start.teamviewer.com/{tv_id}")
                else:
                    subprocess.Popen(["mstsc", f"/v:{ip}"])
            elif action == "remote_desktop":
                subprocess.Popen(["mstsc", f"/v:{ip}"])
            elif action == "ssh":
                self._open_ssh(ip, ssh_user)
            else:
                webbrowser.open(web_url or self._fallback_web_url(ip, subtype))
        except Exception as exc:
            LOGGER.exception("Erreur ouverture URL serveur : %s", exc)
            messagebox.showerror("Erreur", f"Impossible d'ouvrir {dev.ip}")

    def _on_selection_mutual(self, _evt=None) -> None:
        try:
            self.parent.master.switch_view.tree.selection_remove(
                *self.parent.master.switch_view.tree.selection()
            )
        except Exception:
            pass
        try:
            self.parent.master.consolidated_app.tree.selection_remove(
                *self.parent.master.consolidated_app.tree.selection()
            )
        except Exception:
            pass
