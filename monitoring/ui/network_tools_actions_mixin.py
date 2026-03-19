from __future__ import annotations

import queue
import subprocess
import threading
import tkinter as tk
from tkinter import Button, Frame, Menu, simpledialog
from tkinter.scrolledtext import ScrolledText

from monitoring.ui.theme_utils import apply_control_button_style, bind_blue_hover


class NetworkToolsActionsMixin:
    def _show_tool_output(self, title: str, output: str) -> None:
        """Affiche le resultat d'un outil reseau."""
        win, txt = self._create_tool_output_window(title)
        txt.insert("1.0", output or "Aucune sortie.")
        txt.configure(state="disabled")

    def _create_tool_output_window(
        self,
        title: str,
        *,
        initial_text: str = "",
        geometry: str = "760x480",
    ):
        win = tk.Toplevel(self.parent)
        win.title(title)
        win.geometry(geometry)
        c = self.theme.colors
        win.configure(bg=c["app_bg"])
        txt = ScrolledText(win, wrap="word")
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.configure(bg=c["tree_bg"], fg=c["tree_fg"], insertbackground=c["tree_fg"])
        if initial_text:
            txt.insert("1.0", initial_text)
        txt.configure(state="disabled")
        return win, txt

    @staticmethod
    def _spawn_tool_thread(worker, *, name: str) -> None:
        threading.Thread(target=worker, daemon=True, name=name).start()

    @staticmethod
    def _stop_process(proc) -> None:
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    @staticmethod
    def _append_tool_line(txt: ScrolledText, line: str) -> None:
        txt.configure(state="normal")
        txt.insert("end", line + "\n")
        txt.see("end")
        txt.configure(state="disabled")

    def _poll_tool_events(
        self,
        win,
        txt: ScrolledText,
        events: queue.Queue,
        *,
        title: str,
        success_label: str = "OK",
        failure_label: str = "ECHEC",
        delay_ms: int = 120,
    ) -> None:
        if not win.winfo_exists():
            return
        try:
            while True:
                kind, payload = events.get_nowait()
                if kind == "line":
                    self._append_tool_line(txt, str(payload))
                elif kind == "done":
                    status = success_label if payload else failure_label
                    win.title(f"{title} - {status}")
        except queue.Empty:
            pass
        win.after(
            delay_ms,
            lambda: self._poll_tool_events(
                win,
                txt,
                events,
                title=title,
                success_label=success_label,
                failure_label=failure_label,
                delay_ms=delay_ms,
            ),
        )

    def _run_network_tool(self, title: str, runner) -> None:
        ok, output = runner()
        status = "OK" if ok else "ECHEC"
        self._show_tool_output(f"{title} - {status}", output)

    def _run_network_tool_stream(self, title: str, runner_stream) -> None:
        """Lance un outil reseau avec affichage progressif en temps reel."""
        win, txt = self._create_tool_output_window(title, initial_text="Execution en cours...\n")
        events: queue.Queue = queue.Queue()

        def _push(line: str) -> None:
            events.put(("line", line))

        def _worker() -> None:
            ok = runner_stream(_push)
            events.put(("done", ok))

        self._spawn_tool_thread(_worker, name=f"Tool-{title}")
        self._poll_tool_events(win, txt, events, title=title)

    def _run_ping_tool_stream(self, ip: str) -> None:
        """Lance un ping continu et permet de l'arreter proprement."""
        win, txt = self._create_tool_output_window(
            "Ping (continu)",
            initial_text=f"Execution ping -t vers {ip}...\n",
            geometry="760x520",
        )
        c = self.theme.colors

        controls = Frame(win, bg=c["app_bg"])
        controls.pack(fill="x", padx=8, pady=(0, 8))

        events: queue.Queue = queue.Queue()
        stop_event = threading.Event()
        proc_holder: dict[str, subprocess.Popen] = {}

        def _on_start(proc) -> None:
            proc_holder["proc"] = proc

        def _push(line: str) -> None:
            events.put(("line", line))

        def _stop_and_close() -> None:
            stop_event.set()
            self._stop_process(proc_holder.get("proc"))
            if win.winfo_exists():
                win.destroy()

        controls.grid_columnconfigure(0, weight=1)
        btn_stop = Button(
            controls,
            text="Stop",
            command=_stop_and_close,
            relief="raised",
            bd=1,
        )
        btn_stop.grid(row=0, column=0)
        apply_control_button_style(btn_stop, c, hovered=False)
        bind_blue_hover(btn_stop, lambda: self.theme.colors)

        def _worker() -> None:
            ok = self.network_tools.stream_ping(
                ip,
                _push,
                continuous=True,
                stop_event=stop_event,
                on_start=_on_start,
            )
            events.put(("done", ok))

        win.protocol("WM_DELETE_WINDOW", _stop_and_close)
        self._spawn_tool_thread(_worker, name="Tool-PingContinuous")
        self._poll_tool_events(win, txt, events, title="Ping (continu)", failure_label="Arrete")

    def _new_context_submenu(self, parent_menu: Menu) -> Menu:
        return Menu(
            parent_menu,
            tearoff=0,
            bg=self.theme.colors["menu_bg"],
            fg=self.theme.colors["menu_fg"],
        )

    def _prompt_network_port(self, ip: str) -> int | None:
        return simpledialog.askinteger(
            "Port check",
            f"Port TCP a tester pour {ip}:",
            parent=self.parent,
            minvalue=1,
            maxvalue=65535,
        )

    def _prompt_network_string(self, *, title: str, prompt: str, initialvalue: str) -> str | None:
        value = simpledialog.askstring(
            title,
            prompt,
            initialvalue=initialvalue,
            parent=self.parent,
        )
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    def _run_port_check_prompt(self, ip: str) -> None:
        port = self._prompt_network_port(ip)
        if port is None:
            return
        self._run_network_tool("Port check", lambda: self.network_tools.port_check(ip, port))

    def _run_dns_lookup_prompt(self, ip: str) -> None:
        target = self._prompt_network_string(
            title="DNS lookup",
            prompt="Domaine ou IP a resoudre:",
            initialvalue=ip,
        )
        if target is None:
            return
        self._run_network_tool_stream(
            "DNS lookup",
            lambda on_line: self.network_tools.stream_dns_lookup(target, on_line),
        )

    def _run_http_check_prompt(self, ip: str) -> None:
        url = self._prompt_network_string(
            title="HTTP(S) check",
            prompt="URL a verifier (certificat si HTTPS):",
            initialvalue=f"http://{ip}",
        )
        if url is None:
            return
        self._run_network_tool("HTTP(S) check", lambda: self.network_tools.http_check(url))

    def _run_snmp_check_prompt(self, ip: str) -> None:
        community = self._prompt_network_string(
            title="SNMP",
            prompt="Community:",
            initialvalue="public",
        )
        if community is None:
            return
        oid = self._prompt_network_string(
            title="SNMP",
            prompt="OID:",
            initialvalue="1.3.6.1.2.1.1.1.0",
        )
        if oid is None:
            return
        self._run_network_tool("SNMP", lambda: self.network_tools.snmp_check(ip, community, oid))

    def _network_tools_menu_actions(self, ip: str) -> list[tuple[str, object]]:
        return [
            ("Ping", lambda: self._run_ping_tool_stream(ip)),
            ("Port check", lambda: self._run_port_check_prompt(ip)),
            (
                "Traceroute",
                lambda: self._run_network_tool_stream(
                    "Traceroute",
                    lambda on_line: self.network_tools.stream_traceroute(ip, on_line),
                ),
            ),
            ("DNS lookup", lambda: self._run_dns_lookup_prompt(ip)),
            ("HTTP(S) check (avec certificat)", lambda: self._run_http_check_prompt(ip)),
            ("SNMP", lambda: self._run_snmp_check_prompt(ip)),
        ]

    def _add_network_tools_submenu(self, menu: Menu, ip: str, *, at_index: int | None = None) -> None:
        """Ajoute le sous-menu Outils Reseau au menu contextuel."""
        tools = self._new_context_submenu(menu)
        for label, command in self._network_tools_menu_actions(ip):
            tools.add_command(label=label, command=command)

        if at_index is None:
            menu.add_cascade(label="Outils Réseau", menu=tools)
        else:
            menu.insert_cascade(at_index, label="Outils Réseau", menu=tools)
