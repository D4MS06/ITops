from __future__ import annotations

import ipaddress
import threading
from tkinter import BooleanVar, Frame, Label, Menu, StringVar, messagebox, ttk

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.network_scan_service import NetworkScanService
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.dialogs.themed_dialog import ThemedDialog


class NetworkScanDialog(ThemedDialog):
    def __init__(
        self,
        parent,
        *,
        model: DevicesModel,
        controller: AppController,
    ) -> None:
        self.model = model
        self.controller = controller
        self._scan_service = NetworkScanService()
        self.var_mode = StringVar(value="vlan")
        self.var_vlan = StringVar(value="1")
        self.var_start_ip = StringVar(value="192.168.1.1")
        self.var_end_ip = StringVar(value="192.168.1.254")
        self.var_status = StringVar(value="Pret.")
        self.var_vendor_online = BooleanVar(value=False)
        self._rows_by_iid: dict[str, dict] = {}
        self._scan_thread: threading.Thread | None = None
        self._scan_stop = threading.Event()
        self._scan_total = 0
        self._scan_done = 0
        self._scan_found = 0
        self._closing_requested = False
        self._known_device_ips: set[str] = set()
        super().__init__(parent, title="Scan reseau")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(2, weight=1)

        params = Frame(master)
        params.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        params.grid_columnconfigure(4, weight=1)

        ttk.Radiobutton(params, text="VLAN", value="vlan", variable=self.var_mode, command=self._sync_mode).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ttk.Radiobutton(params, text="Plage manuelle", value="manual", variable=self.var_mode, command=self._sync_mode).grid(
            row=0, column=1, sticky="w"
        )

        Label(params, text="VLAN:").grid(row=1, column=0, sticky="e", padx=(0, 4), pady=(6, 0))
        self.entry_vlan = ttk.Entry(params, textvariable=self.var_vlan, width=8)
        self.entry_vlan.grid(row=1, column=1, sticky="w", pady=(6, 0))

        Label(params, text="Debut IP:").grid(row=1, column=2, sticky="e", padx=(12, 4), pady=(6, 0))
        self.entry_start = ttk.Entry(params, textvariable=self.var_start_ip, width=16)
        self.entry_start.grid(row=1, column=3, sticky="w", pady=(6, 0))

        Label(params, text="Fin IP:").grid(row=1, column=4, sticky="e", padx=(12, 4), pady=(6, 0))
        self.entry_end = ttk.Entry(params, textvariable=self.var_end_ip, width=16)
        self.entry_end.grid(row=1, column=5, sticky="w", pady=(6, 0))
        ttk.Checkbutton(params, text="Fabricants en ligne", variable=self.var_vendor_online).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        actions = Frame(master)
        actions.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))
        self.btn_scan = ttk.Button(actions, text="Scanner", command=self._start_scan)
        self.btn_scan.pack(side="left")
        self.btn_stop = ttk.Button(actions, text="Arreter", command=self._stop_scan, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.progress = ttk.Progressbar(actions, mode="determinate", length=180)
        self.progress.pack(side="left", padx=(10, 0))
        Label(actions, textvariable=self.var_status).pack(side="left", padx=(12, 0))

        table = Frame(master)
        table.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(table, columns=("ip", "hostname", "vendor", "mac"), show="headings", selectmode="browse")
        self.tree.heading("ip", text="IP")
        self.tree.heading("hostname", text="Nom")
        self.tree.heading("vendor", text="Fabricant")
        self.tree.heading("mac", text="MAC")
        self.tree.column("ip", width=150, minwidth=120, stretch=False)
        self.tree.column("hostname", width=220, minwidth=140, stretch=True)
        self.tree.column("vendor", width=220, minwidth=150, stretch=True)
        self.tree.column("mac", width=170, minwidth=140, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Button-3>", self._on_context_menu)

        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        self._refresh_known_device_ips()
        self._configure_scan_row_tags()
        self._sync_mode()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        ttk.Button(box, text="Fermer", command=self.cancel, style="Dialog.TButton").pack(padx=6, pady=8)
        box.pack()

    def cancel(self, event=None) -> None:
        self._closing_requested = True
        self._scan_stop.set()
        if self._scan_thread is not None and self._scan_thread.is_alive():
            self._set_scan_running(False)
            self.var_status.set("Arret en cours...")
            self.after(120, self._close_when_scan_stopped)
            return
        super().cancel(event)

    def _close_when_scan_stopped(self) -> None:
        if self._scan_thread is not None and self._scan_thread.is_alive():
            self.after(120, self._close_when_scan_stopped)
            return
        try:
            super().cancel()
        except Exception:
            pass

    def _sync_mode(self) -> None:
        mode = self.var_mode.get().strip().lower()
        is_vlan = mode == "vlan"
        self.entry_vlan.configure(state="normal" if is_vlan else "disabled")
        self.entry_start.configure(state="disabled" if is_vlan else "normal")
        self.entry_end.configure(state="disabled" if is_vlan else "normal")
        if is_vlan:
            self._apply_vlan_range()

    def _apply_vlan_range(self) -> None:
        try:
            start_ip, end_ip = self._scan_service.vlan_to_range(int(self.var_vlan.get().strip()))
        except Exception:
            return
        self.var_start_ip.set(start_ip)
        self.var_end_ip.set(end_ip)

    def _resolve_target_range(self) -> tuple[str, str]:
        mode = self.var_mode.get().strip().lower()
        if mode == "vlan":
            vlan = int(self.var_vlan.get().strip())
            return self._scan_service.vlan_to_range(vlan)
        start_ip = self.var_start_ip.get().strip()
        end_ip = self.var_end_ip.get().strip()
        self._scan_service.normalize_range(start_ip, end_ip)
        return start_ip, end_ip

    def _set_scan_running(self, running: bool) -> None:
        self.btn_scan.configure(state="disabled" if running else "normal")
        self.btn_stop.configure(state="normal" if running else "disabled")
        if not running:
            self.progress.configure(maximum=max(1, self._scan_total), value=self._scan_done)

    def _stop_scan(self) -> None:
        if self._scan_thread is None or not self._scan_thread.is_alive():
            self._set_scan_running(False)
            self.var_status.set("Pret.")
            return
        self._scan_stop.set()
        self.var_status.set("Arret en cours...")

    def _start_scan(self) -> None:
        if self._scan_thread is not None and not self._scan_thread.is_alive():
            self._scan_thread = None
        if self._scan_thread is not None and self._scan_thread.is_alive():
            return
        try:
            start_ip, end_ip = self._resolve_target_range()
        except Exception as exc:
            messagebox.showerror("Scan reseau", f"Parametres invalides: {exc}", parent=self)
            return

        self._scan_stop.clear()
        self._refresh_known_device_ips()
        self._rows_by_iid.clear()
        self._scan_done = 0
        self._scan_found = 0
        self._scan_total = int(int(ipaddress.ip_address(end_ip)) - int(ipaddress.ip_address(start_ip)) + 1)
        self.progress.configure(maximum=max(1, self._scan_total), value=0)
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.var_status.set(f"Scan {start_ip} -> {end_ip} ...")
        self._set_scan_running(True)

        def _progress(done: int, total: int) -> None:
            self.after(0, lambda: self._on_progress(done, total))

        def _report(row: dict) -> None:
            self.after(0, lambda: self._upsert_row(row))

        def _task() -> None:
            rows: list[dict] = []
            error: Exception | None = None
            try:
                rows = self._scan_service.scan_range(
                    start_ip=start_ip,
                    end_ip=end_ip,
                    allow_vendor_network=bool(self.var_vendor_online.get()),
                    stop_event=self._scan_stop,
                    progress_cb=_progress,
                    report_cb=_report,
                )
            except Exception as exc:
                error = exc
            try:
                self.after(0, lambda: self._on_scan_finished(rows, error))
            except Exception:
                pass

        self._scan_thread = threading.Thread(target=_task, daemon=True)
        self._scan_thread.start()

    def _on_scan_finished(self, rows: list[dict], error: Exception | None = None) -> None:
        self._scan_thread = None
        self._set_scan_running(False)
        if self._closing_requested:
            try:
                super().cancel()
            except Exception:
                pass
            return
        if error is not None:
            self.var_status.set("Erreur pendant le scan.")
            messagebox.showerror("Scan reseau", f"Echec du scan: {error}", parent=self)
            return
        if self._scan_stop.is_set():
            self.var_status.set("Scan annule.")
            return
        for row in rows:
            self._upsert_row(row)
        self.progress.configure(value=self._scan_total)
        self.var_status.set(f"Scan termine: {self._scan_found} hote(s) detecte(s).")

    def _on_progress(self, done: int, total: int) -> None:
        self._scan_done = max(0, int(done))
        if int(total) > 0:
            self._scan_total = int(total)
        self.progress.configure(maximum=max(1, self._scan_total), value=min(self._scan_done, self._scan_total))
        self.var_status.set(f"Scan en cours: {self._scan_done}/{self._scan_total} | trouves: {self._scan_found}")

    def _upsert_row(self, row: dict) -> None:
        ip = str(row.get("ip", "")).strip()
        if not ip:
            return
        iid = ip
        previous = self._rows_by_iid.get(iid, {})
        merged = {
            "ip": ip,
            "hostname": str(row.get("hostname", "") or previous.get("hostname", "")),
            "vendor": str(row.get("vendor", "") or previous.get("vendor", "")),
            "mac": str(row.get("mac", "") or previous.get("mac", "")),
        }
        is_new = iid not in self._rows_by_iid
        self._rows_by_iid[iid] = merged
        values = (merged["ip"], merged["hostname"], merged["vendor"], merged["mac"])
        tag = self._scan_row_tag_for_ip(ip)
        if self.tree.exists(iid):
            self.tree.item(iid, values=values, tags=(tag,))
        else:
            self.tree.insert("", "end", iid=iid, values=values, tags=(tag,))
        if is_new:
            self._scan_found += 1
            self.var_status.set(
                f"Scan en cours: {self._scan_done}/{self._scan_total} | trouves: {self._scan_found} (dernier: {ip})"
            )

    def _selected_row(self) -> tuple[str | None, dict | None]:
        sel = self.tree.selection()
        iid = str(sel[0]) if sel else str(self.tree.focus() or "")
        iid = iid.strip()
        if not iid:
            return None, None
        return iid, self._rows_by_iid.get(iid)

    def _on_context_menu(self, event) -> None:
        row_id = str(self.tree.identify_row(event.y))
        if row_id:
            self.tree.selection_set(row_id)
            self.tree.focus(row_id)
        _iid, row = self._selected_row()
        if row is None:
            return
        menu = Menu(
            self,
            tearoff=0,
            bg=self.theme.colors["menu_bg"],
            fg=self.theme.colors["menu_fg"],
        )
        menu.add_command(label="Ajouter en device", command=self._add_selected_as_device)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass

    def _add_selected_as_device(self) -> None:
        _iid, row = self._selected_row()
        if row is None:
            return
        ip = str(row.get("ip", "")).strip()
        host = str(row.get("hostname", "")).strip()
        vendor = str(row.get("vendor", "")).strip()
        mac = str(row.get("mac", "")).strip()
        if not ip:
            return
        initial = {
            "name": host or ip,
            "ip": ip,
            "desc": self._build_device_desc(mac=mac, vendor=vendor),
            "notify": True,
            "custom_data": {},
        }
        dialog = DeviceForm(
            self.parent,
            title="Ajouter un equipement (scan reseau)",
            initial=initial,
            lock_type_on_initial=False,
        )
        if dialog.result is None:
            return
        dtype = str(dialog.result.get("kind", "")).strip().lower()
        if not dtype:
            messagebox.showerror("Scan reseau", "Type de device manquant.", parent=self)
            return
        created = self.model.add_device(
            dtype,
            str(dialog.result.get("name", "")),
            str(dialog.result.get("ip", "")),
            str(dialog.result.get("desc", "")),
            id_Teamviewer=str(dialog.result.get("tv_id", "")),
            device_subtype=str(dialog.result.get("subtype", "")),
            action_double_click=str(dialog.result.get("action_double_click", "")),
            web_url=str(dialog.result.get("web_url", "")),
            ssh_user=str(dialog.result.get("ssh_user", "")),
            custom_data=dict(dialog.result.get("custom_data", {}) or {}),
            notify=bool(dialog.result.get("notify", True)),
        )
        if not created:
            messagebox.showwarning("Scan reseau", "Adresse IP deja utilisee pour ce type.", parent=self)
            return
        self._refresh_known_device_ips()
        self._apply_scan_row_tags()
        self.controller.refresh_views()
        messagebox.showinfo("Scan reseau", "Peripherique ajoute.", parent=self)

    @staticmethod
    def _build_device_desc(*, mac: str, vendor: str) -> str:
        parts = ["Decouvert par scan reseau"]
        if mac:
            parts.append(f"MAC: {mac}")
        if vendor:
            parts.append(f"Fabricant: {vendor}")
        return " | ".join(parts)

    def _refresh_known_device_ips(self) -> None:
        ips: set[str] = set()
        try:
            for row in self.model.list_devices():
                normalized = self._normalize_ip_for_match(str((row or {}).get("ip", "")))
                if normalized:
                    ips.add(normalized)
        except Exception:
            ips = set()
        self._known_device_ips = ips

    def _scan_row_tag_for_ip(self, ip: str) -> str:
        normalized = self._normalize_ip_for_match(ip)
        return "scan_known_device" if normalized and normalized in self._known_device_ips else "scan_new_device"

    def _configure_scan_row_tags(self) -> None:
        c = self.theme.colors
        base_bg = c.get("tree_bg", "#ffffff")
        strong_known_bg = c.get("control_hover_bg", c.get("tree_select_bg", "#93c5fd"))
        known_fg = c.get("control_hover_fg", c.get("text_primary", "#0f172a"))
        if str(getattr(self.theme, "key", "")).strip().lower() == "dark":
            strong_new_bg = "#8a6b00"
            new_fg = "#ffffff"
        else:
            strong_new_bg = "#fde68a"
            new_fg = c.get("text_primary", "#0f172a")
        known_bg = self._blend_hex(strong_known_bg, base_bg, alpha=0.42)
        new_bg = self._blend_hex(strong_new_bg, base_bg, alpha=0.38)
        self.tree.tag_configure("scan_known_device", background=known_bg, foreground=known_fg)
        self.tree.tag_configure("scan_new_device", background=new_bg, foreground=new_fg)

    def _apply_scan_row_tags(self) -> None:
        for iid, row in list(self._rows_by_iid.items()):
            ip = str((row or {}).get("ip", "")).strip()
            if not ip or not self.tree.exists(iid):
                continue
            self.tree.item(iid, tags=(self._scan_row_tag_for_ip(ip),))

    @staticmethod
    def _normalize_ip_for_match(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        try:
            return str(ipaddress.ip_address(raw))
        except Exception:
            return raw

    @staticmethod
    def _blend_hex(fg_hex: str, bg_hex: str, *, alpha: float) -> str:
        def _parse(value: str) -> tuple[int, int, int]:
            text = str(value or "").strip().lstrip("#")
            if len(text) == 3:
                text = "".join(ch * 2 for ch in text)
            if len(text) != 6:
                return (255, 255, 255)
            try:
                return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
            except Exception:
                return (255, 255, 255)

        a = max(0.0, min(1.0, float(alpha)))
        fr, fg, fb = _parse(fg_hex)
        br, bg, bb = _parse(bg_hex)
        rr = int(round((a * fr) + ((1.0 - a) * br)))
        rg = int(round((a * fg) + ((1.0 - a) * bg)))
        rb = int(round((a * fb) + ((1.0 - a) * bb)))
        return f"#{rr:02x}{rg:02x}{rb:02x}"
