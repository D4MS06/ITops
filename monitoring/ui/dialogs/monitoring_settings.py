from __future__ import annotations

from tkinter import ACTIVE, BooleanVar, Button, Checkbutton, Entry, Frame, Label, LabelFrame, StringVar
from tkinter import messagebox as mb

from monitoring.ui.dialogs.themed_dialog import ThemedDialog


class MonitoringSettingsDialog(ThemedDialog):
    """Dialog modal pour configurer monitoring, notifications et logs diagnostics."""

    def __init__(
        self,
        parent,
        offline_delay_seconds: int,
        online_recovery_delay_seconds: int,
        notification_cooldown_seconds: int,
        failures_for_offline: int,
        successes_for_online: int,
        ping_timeout_ms: int,
        probe_interval_ms: int,
        log_diagnostic_events: bool,
    ) -> None:
        self.offline_delay_seconds = max(1, int(offline_delay_seconds or 5))
        self.online_recovery_delay_seconds = max(
            1, int(online_recovery_delay_seconds or self.offline_delay_seconds)
        )
        self.notification_cooldown_seconds = max(0, int(notification_cooldown_seconds or 0))
        self.failures_for_offline = max(1, int(failures_for_offline or 3))
        self.successes_for_online = max(1, int(successes_for_online or 2))
        self.ping_timeout_ms = max(250, int(ping_timeout_ms or 1500))
        self.probe_interval_ms = max(250, int(probe_interval_ms or 1000))
        self.log_diagnostic_events = bool(log_diagnostic_events)
        self.result: dict[str, int | bool] | None = None
        super().__init__(parent, title="Parametres monitoring, alertes et logs")

    def body(self, master: Frame) -> Frame:
        self.var_offline_delay = StringVar(value=str(self.offline_delay_seconds))
        self.var_online_delay = StringVar(value=str(self.online_recovery_delay_seconds))
        self.var_cooldown = StringVar(value=str(self.notification_cooldown_seconds))
        self.var_fails = StringVar(value=str(self.failures_for_offline))
        self.var_successes = StringVar(value=str(self.successes_for_online))
        self.var_ping_timeout = StringVar(value=str(self.ping_timeout_ms))
        self.var_probe_interval = StringVar(value=str(self.probe_interval_ms))
        self.var_log_diag = BooleanVar(value=self.log_diagnostic_events)

        def add_row(parent: Frame, row: int, title: str, variable: StringVar, unit: str) -> None:
            Label(parent, text=title, anchor="w").grid(row=row, column=0, sticky="w", padx=(8, 6), pady=4)
            Entry(parent, textvariable=variable, width=10, justify="right").grid(
                row=row, column=1, sticky="e", padx=(0, 6), pady=4
            )
            Label(parent, text=unit, anchor="w", width=4).grid(row=row, column=2, sticky="w", padx=(0, 8), pady=4)

        mon = LabelFrame(master, text="Monitoring (detection / anti faux-positifs)", padx=4, pady=4)
        mon.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        mon.grid_columnconfigure(0, weight=1)
        add_row(mon, 0, "Bascule OFFLINE apres", self.var_offline_delay, "sec")
        add_row(mon, 1, "Retour ONLINE stable apres", self.var_online_delay, "sec")
        add_row(mon, 2, "Echecs consecutifs (OFFLINE)", self.var_fails, "x")
        add_row(mon, 3, "Succes consecutifs (ONLINE)", self.var_successes, "x")
        add_row(mon, 4, "Timeout ping", self.var_ping_timeout, "ms")
        add_row(mon, 5, "Intervalle entre sondes", self.var_probe_interval, "ms")

        notif = LabelFrame(master, text="Notifications (anti-spam)", padx=4, pady=4)
        notif.grid(row=1, column=0, sticky="ew", padx=8, pady=6)
        notif.grid_columnconfigure(0, weight=1)
        add_row(notif, 0, "Cooldown alertes par equipement", self.var_cooldown, "sec")
        Label(
            notif,
            text="0 = pas de limitation de frequence",
            fg="#5f6b7a",
            anchor="w",
        ).grid(row=1, column=0, columnspan=3, sticky="w", padx=(8, 6), pady=(0, 2))

        logs = LabelFrame(master, text="Logs diagnostics", padx=4, pady=4)
        logs.grid(row=2, column=0, sticky="ew", padx=8, pady=(6, 8))
        logs.grid_columnconfigure(0, weight=1)
        Checkbutton(
            logs,
            text="Activer le journal diagnostic (micro-coupures)",
            variable=self.var_log_diag,
        ).grid(row=0, column=0, sticky="w", padx=8, pady=4)

        master.grid_columnconfigure(0, weight=1)
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        btn_ok = Button(box, text="OK", width=10, command=self.ok, default=ACTIVE)
        btn_ok.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Annuler", width=10, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        for btn in (btn_ok, btn_cancel):
            self.style_button(btn)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
        self.apply_theme(self)

    def validate(self) -> bool:
        raw_offline = self.var_offline_delay.get().strip()
        raw_online = self.var_online_delay.get().strip()
        raw_cooldown = self.var_cooldown.get().strip()
        raw_fails = self.var_fails.get().strip()
        raw_successes = self.var_successes.get().strip()
        raw_ping_timeout = self.var_ping_timeout.get().strip()
        raw_probe_interval = self.var_probe_interval.get().strip()
        try:
            offline_delay = int(raw_offline)
            online_delay = int(raw_online)
            cooldown = int(raw_cooldown)
            fails = int(raw_fails)
            successes = int(raw_successes)
            ping_timeout = int(raw_ping_timeout)
            probe_interval = int(raw_probe_interval)
        except Exception:
            mb.showerror("Valeur invalide", "Entrez des nombres entiers valides.")
            return False
        if offline_delay < 1:
            mb.showerror("Valeur invalide", "Le delai doit etre superieur ou egal a 1 seconde.")
            return False
        if online_delay < 1:
            mb.showerror(
                "Valeur invalide",
                "Le delai de retour en ligne doit etre superieur ou egal a 1 seconde.",
            )
            return False
        if cooldown < 0:
            mb.showerror(
                "Valeur invalide",
                "La frequence max des alertes par equipement doit etre superieure ou egale a 0 seconde.",
            )
            return False
        if fails < 1:
            mb.showerror("Valeur invalide", "Les echecs consecutifs doivent etre >= 1.")
            return False
        if successes < 1:
            mb.showerror("Valeur invalide", "Les succes consecutifs doivent etre >= 1.")
            return False
        if ping_timeout < 250:
            mb.showerror("Valeur invalide", "Le timeout ping doit etre >= 250 ms.")
            return False
        if probe_interval < 250:
            mb.showerror("Valeur invalide", "L'intervalle entre sondes doit etre >= 250 ms.")
            return False
        self.result = {
            "offline_delay_seconds": offline_delay,
            "online_recovery_delay_seconds": online_delay,
            "notification_cooldown_seconds": cooldown,
            "failures_for_offline": fails,
            "successes_for_online": successes,
            "ping_timeout_ms": ping_timeout,
            "probe_interval_ms": probe_interval,
            "log_diagnostic_events": 1 if self.var_log_diag.get() else 0,
        }
        return True
