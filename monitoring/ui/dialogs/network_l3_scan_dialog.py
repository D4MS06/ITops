from __future__ import annotations

import threading
from tkinter import BooleanVar, Frame, Label, Menu, StringVar, messagebox, ttk

from monitoring.controllers.app_controller import AppController
from monitoring.models.devices_model import DevicesModel
from monitoring.services.l3_router_scan_service import L3RouterScanService
from monitoring.services.network_scan_service import NetworkScanService
from monitoring.ui.dialogs.device_form import DeviceForm
from monitoring.ui.dialogs.themed_dialog import ThemedDialog


class NetworkL3ScanDialog(ThemedDialog):
    COMMAND_PROFILES: dict[str, tuple[str, str]] = {
        "hpe_comware": ("HPE Comware", "display arp"),
        "cisco_ios": ("Cisco IOS", "show ip arp"),
        "mikrotik_ros": ("MikroTik RouterOS", "ip arp print without-paging"),
        "custom": ("Personnalise", ""),
    }
    PROFILE_ORDER = ("hpe_comware", "cisco_ios", "mikrotik_ros", "custom")

    def __init__(self, parent, *, model: DevicesModel, controller: AppController) -> None:
        self.model = model
        self.controller = controller
        self._scan_service = L3RouterScanService()
        self._range_service = NetworkScanService()
        self.var_mode = StringVar(value="all")
        self.var_router_host = StringVar(value="")
        self.var_router_user = StringVar(value="")
        self.var_profile = StringVar(value=self.COMMAND_PROFILES["hpe_comware"][0])
        self.var_router_cmd = StringVar(value=self.COMMAND_PROFILES["hpe_comware"][1])
        self.var_vlan = StringVar(value="11")
        self.var_start_ip = StringVar(value="192.168.11.1")
        self.var_end_ip = StringVar(value="192.168.11.254")
        self.var_status = StringVar(value="Pret.")
        self.var_vendor_online = BooleanVar(value=False)
        self._rows_by_iid: dict[str, dict] = {}
        self._scan_thread: threading.Thread | None = None
        self._scan_stop = threading.Event()
        self._scan_total = 0
        self._scan_done = 0
        self._scan_found = 0
        self._closing_requested = False
        self._profile_label_to_key = {label: key for key, (label, _cmd) in self.COMMAND_PROFILES.items()}
        super().__init__(parent, title="Scan avance L3")

    def body(self, master) -> Frame:
        master.grid_columnconfigure(0, weight=1)
        master.grid_rowconfigure(2, weight=1)

        params = Frame(master)
        params.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        for col in range(8):
            params.grid_columnconfigure(col, weight=1 if col in {3, 7} else 0)

        Label(params, text="Equipement L3:").grid(row=0, column=0, sticky="e", padx=(0, 4))
        self.entry_host = ttk.Entry(params, textvariable=self.var_router_host, width=18)
        self.entry_host.grid(row=0, column=1, sticky="w")
        Label(params, text="User SSH:").grid(row=0, column=2, sticky="e", padx=(12, 4))
        self.entry_user = ttk.Entry(params, textvariable=self.var_router_user, width=14)
        self.entry_user.grid(row=0, column=3, sticky="w")
        Label(params, text="Profil:").grid(row=0, column=4, sticky="e", padx=(12, 4))
        self.combo_profile = ttk.Combobox(
            params,
            textvariable=self.var_profile,
            values=[self.COMMAND_PROFILES[key][0] for key in self.PROFILE_ORDER],
            state="readonly",
            width=14,
        )
        self.combo_profile.grid(row=0, column=5, sticky="w")
        self.combo_profile.bind("<<ComboboxSelected>>", self._on_profile_changed)
        Label(params, text="Commande ARP:").grid(row=0, column=6, sticky="e", padx=(12, 4))
        self.entry_cmd = ttk.Entry(params, textvariable=self.var_router_cmd, width=26)
        self.entry_cmd.grid(row=0, column=7, sticky="ew")

        ttk.Radiobutton(params, text="Tout", value="all", variable=self.var_mode, command=self._sync_mode).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Radiobutton(params, text="VLAN", value="vlan", variable=self.var_mode, command=self._sync_mode).grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )
        ttk.Radiobutton(params, text="Plage manuelle", value="manual", variable=self.var_mode, command=self._sync_mode).grid(
            row=1, column=2, sticky="w", pady=(8, 0)
        )

        Label(params, text="VLAN:").grid(row=2, column=0, sticky="e", padx=(0, 4), pady=(6, 0))
        self.entry_vlan = ttk.Entry(params, textvariable=self.var_vlan, width=8)
        self.entry_vlan.grid(row=2, column=1, sticky="w", pady=(6, 0))
        Label(params, text="Debut IP:").grid(row=2, column=2, sticky="e", padx=(12, 4), pady=(6, 0))
        self.entry_start = ttk.Entry(params, textvariable=self.var_start_ip, width=16)
        self.entry_start.grid(row=2, column=3, sticky="w", pady=(6, 0))
        Label(params, text="Fin IP:").grid(row=2, column=4, sticky="e", padx=(12, 4), pady=(6, 0))
        self.entry_end = ttk.Entry(params, textvariable=self.var_end_ip, width=16)
        self.entry_end.grid(row=2, column=5, sticky="w", pady=(6, 0))
        ttk.Checkbutton(params, text="Fabricants en ligne", variable=self.var_vendor_online).grid(
            row=2, column=6, columnspan=2, sticky="w", padx=(12, 0), pady=(6, 0)
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

        self.tree = ttk.Treeview(table, columns=("ip", "hostname", "vendor", "mac", "iface"), show="headings", selectmode="browse")
        self.tree.heading("ip", text="IP")
        self.tree.heading("hostname", text="Nom")
        self.tree.heading("vendor", text="Fabricant")
        self.tree.heading("mac", text="MAC")
        self.tree.heading("iface", text="Interface")
        self.tree.column("ip", width=135, minwidth=120, stretch=False)
        self.tree.column("hostname", width=180, minwidth=140, stretch=True)
        self.tree.column("vendor", width=200, minwidth=150, stretch=True)
        self.tree.column("mac", width=170, minwidth=140, stretch=False)
        self.tree.column("iface", width=100, minwidth=80, stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Button-3>", self._on_context_menu)

        vsb = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.grid(row=0, column=1, sticky="ns")

        self._sync_mode()
        self._apply_profile()
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
        is_manual = mode == "manual"
        self.entry_vlan.configure(state="normal" if is_vlan else "disabled")
        self.entry_start.configure(state="normal" if is_manual else "disabled")
        self.entry_end.configure(state="normal" if is_manual else "disabled")
        if is_vlan:
            self._apply_vlan_range()

    def _on_profile_changed(self, _event=None) -> None:
        self._apply_profile()

    def _apply_profile(self) -> None:
        label = str(self.var_profile.get() or "").strip()
        key = str(self._profile_label_to_key.get(label, "custom")).strip().lower()
        _label, cmd = self.COMMAND_PROFILES.get(key, ("", ""))
        if key != "custom" and cmd:
            self.var_router_cmd.set(cmd)

    def _apply_vlan_range(self) -> None:
        try:
            start_ip, end_ip = self._range_service.vlan_to_range(int(self.var_vlan.get().strip()))
        except Exception:
            return
        self.var_start_ip.set(start_ip)
        self.var_end_ip.set(end_ip)

    def _resolve_filter_range(self) -> tuple[str | None, str | None]:
        mode = self.var_mode.get().strip().lower()
        if mode == "all":
            return None, None
        if mode == "vlan":
            return self._range_service.vlan_to_range(int(self.var_vlan.get().strip()))
        start_ip = self.var_start_ip.get().strip()
        end_ip = self.var_end_ip.get().strip()
        self._range_service.normalize_range(start_ip, end_ip)
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
        host = self.var_router_host.get().strip()
        if not host:
            messagebox.showerror("Scan avance L3", "Renseignez l'equipement L3.", parent=self)
            return
        ssh_user = self.var_router_user.get().strip()
        command = self.var_router_cmd.get().strip() or "show ip arp"
        try:
            start_ip, end_ip = self._resolve_filter_range()
        except Exception as exc:
            messagebox.showerror("Scan avance L3", f"Filtre invalide: {exc}", parent=self)
            return

        self._scan_stop.clear()
        self._rows_by_iid.clear()
        self._scan_done = 0
        self._scan_found = 0
        self._scan_total = 1
        self.progress.configure(maximum=1, value=0)
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.var_status.set(f"Interrogation L3 {host} ...")
        self._set_scan_running(True)

        def _progress(done: int, total: int) -> None:
            self.after(0, lambda: self._on_progress(done, total))

        def _report(row: dict) -> None:
            self.after(0, lambda: self._upsert_row(row))

        def _task() -> None:
            rows: list[dict] = []
            error: Exception | None = None
            try:
                rows = self._scan_service.scan_router_arp(
                    host=host,
                    ssh_user=ssh_user,
                    command=command,
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
            messagebox.showerror("Scan avance L3", f"Echec du scan: {error}", parent=self)
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
        self._scan_total = max(1, int(total) if int(total) > 0 else 1)
        self.progress.configure(maximum=self._scan_total, value=min(self._scan_done, self._scan_total))
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
            "iface": str(row.get("iface", "") or previous.get("iface", "")),
        }
        is_new = iid not in self._rows_by_iid
        self._rows_by_iid[iid] = merged
        values = (merged["ip"], merged["hostname"], merged["vendor"], merged["mac"], merged["iface"])
        if self.tree.exists(iid):
            self.tree.item(iid, values=values)
        else:
            self.tree.insert("", "end", iid=iid, values=values)
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
        menu = Menu(self, tearoff=0, bg=self.theme.colors["menu_bg"], fg=self.theme.colors["menu_fg"])
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
        iface = str(row.get("iface", "")).strip()
        if not ip:
            return
        initial = {
            "name": host or ip,
            "ip": ip,
            "desc": self._build_device_desc(mac=mac, vendor=vendor, iface=iface),
            "notify": True,
            "custom_data": {},
        }
        dialog = DeviceForm(
            self.parent,
            title="Ajouter un equipement (scan L3)",
            initial=initial,
            lock_type_on_initial=False,
        )
        if dialog.result is None:
            return
        dtype = str(dialog.result.get("kind", "")).strip().lower()
        if not dtype:
            messagebox.showerror("Scan avance L3", "Type de device manquant.", parent=self)
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
            messagebox.showwarning("Scan avance L3", "Adresse IP deja utilisee pour ce type.", parent=self)
            return
        self.controller.refresh_views()
        messagebox.showinfo("Scan avance L3", "Peripherique ajoute.", parent=self)

    @staticmethod
    def _build_device_desc(*, mac: str, vendor: str, iface: str) -> str:
        parts = ["Decouvert par scan avance L3"]
        if mac:
            parts.append(f"MAC: {mac}")
        if vendor:
            parts.append(f"Fabricant: {vendor}")
        if iface:
            parts.append(f"Iface: {iface}")
        return " | ".join(parts)
