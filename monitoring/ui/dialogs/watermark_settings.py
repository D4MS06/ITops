from __future__ import annotations

from pathlib import Path
from tkinter import ACTIVE, HORIZONTAL, Button, Frame, Label, Scale, StringVar, filedialog
from tkinter import messagebox as mb

from monitoring.ui.dialogs.themed_dialog import ThemedDialog


class WatermarkSettingsDialog(ThemedDialog):
    """Dialog de personnalisation de l'image de fond (watermark)."""

    def __init__(
        self,
        parent,
        *,
        current_source_path: str,
        current_rendered_path: str,
        current_opacity: float,
    ) -> None:
        self.source_path = str(current_source_path or "").strip()
        self.rendered_path = str(current_rendered_path or "").strip()
        self.opacity = min(1.0, max(0.0, float(current_opacity or 0.16)))
        self.result: dict[str, object] | None = None
        self._preview_tk = None
        self._cleared = False
        super().__init__(parent, title="Image de fond")

    def body(self, master: Frame) -> Frame:
        current_label_path = self.source_path or self.rendered_path
        self.var_path = StringVar(value=current_label_path or "(aucune image)")
        Label(master, text="Image source:").grid(row=0, column=0, sticky="w", padx=6, pady=(8, 4))
        Label(
            master,
            textvariable=self.var_path,
            fg="#475569",
            anchor="w",
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, columnspan=3, sticky="we", padx=6)

        btn_import = Button(master, text="Importer...", command=self._on_import)
        btn_import.grid(row=0, column=2, sticky="e", padx=6, pady=(8, 4))
        self.style_button(btn_import)

        Label(master, text="Opacite:").grid(row=2, column=0, sticky="w", padx=6, pady=(10, 2))
        self.opacity_scale = Scale(
            master,
            from_=5,
            to=60,
            orient=HORIZONTAL,
            showvalue=True,
            length=340,
            command=self._on_opacity_change,
        )
        self.opacity_scale.set(int(round(self.opacity * 100)))
        self.opacity_scale.grid(row=2, column=1, columnspan=2, sticky="w", padx=6, pady=(10, 2))
        self.opacity_value_label = Label(master, text=f"{self.opacity_scale.get()}%")
        self.opacity_value_label.grid(row=2, column=2, sticky="e", padx=6, pady=(10, 2))

        Label(master, text="Apercu:").grid(row=3, column=0, sticky="w", padx=6, pady=(10, 2))
        self.preview_label = Label(master, bg="#e9edf2", bd=1, relief="solid")
        self.preview_label._theme_skip = True  # type: ignore[attr-defined]
        self.preview_label.grid(row=4, column=0, columnspan=3, sticky="we", padx=6, pady=(2, 8))

        master.grid_columnconfigure(1, weight=1)
        self._refresh_preview()
        self.apply_theme(master)
        return master

    def buttonbox(self) -> None:
        box = Frame(self, bg=self.theme.colors["app_bg"])
        btn_apply = Button(box, text="Appliquer", width=12, command=self.ok, default=ACTIVE)
        btn_apply.pack(side="left", padx=5, pady=5)
        btn_reset = Button(box, text="Reinitialiser", width=12, command=self._on_reset)
        btn_reset.pack(side="left", padx=5, pady=5)
        btn_cancel = Button(box, text="Annuler", width=12, command=self.cancel)
        btn_cancel.pack(side="right", padx=5, pady=5)
        for btn in (btn_apply, btn_reset, btn_cancel):
            self.style_button(btn)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()
        self.apply_theme(self)

    def _on_import(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self,
            title="Choisir une image",
            filetypes=[
                ("Images", "*.png;*.gif;*.jpg;*.jpeg;*.bmp;*.webp"),
                ("PNG", "*.png"),
                ("Tous les fichiers", "*.*"),
            ],
        )
        if not selected:
            return
        self.source_path = selected
        self._cleared = False
        self.var_path.set(selected)
        self._refresh_preview()

    def _on_reset(self) -> None:
        self.source_path = ""
        self.rendered_path = ""
        self._cleared = True
        self.var_path.set("(aucune image)")
        self.opacity_scale.set(16)
        self._refresh_preview()

    def _on_opacity_change(self, _value: str) -> None:
        self.opacity_value_label.config(text=f"{self.opacity_scale.get()}%")
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        try:
            from PIL import Image, ImageEnhance, ImageTk  # type: ignore
        except Exception:
            self.preview_label.configure(
                text="Apercu indisponible: Pillow non installe.",
                image="",
                width=72,
                height=12,
            )
            self._preview_tk = None
            return

        src = self.source_path or self.rendered_path
        if src and Path(src).is_file():
            try:
                wm = Image.open(src).convert("RGBA")
                # Keep exact processing aligned with runtime rendering.
                wm.thumbnail((360, 220), Image.Resampling.LANCZOS)
                alpha = wm.split()[-1]
                target_opacity = min(1.0, max(0.05, float(self.opacity_scale.get()) / 100.0))
                # If source points to the already-rendered watermark, apply a relative factor.
                is_rendered_source = False
                try:
                    if self.rendered_path:
                        is_rendered_source = Path(src).resolve() == Path(self.rendered_path).resolve()
                except Exception:
                    is_rendered_source = False
                if is_rendered_source:
                    baseline = min(1.0, max(0.05, float(self.opacity or 0.16)))
                    factor = target_opacity / baseline
                else:
                    factor = target_opacity
                alpha = ImageEnhance.Brightness(alpha).enhance(factor)
                wm.putalpha(alpha)
                self._preview_tk = ImageTk.PhotoImage(wm)
                self.preview_label.configure(image=self._preview_tk, text="", width=wm.width, height=wm.height)
                self.preview_label.image = self._preview_tk
                return
            except Exception:
                pass

        self.preview_label.configure(
            text="Aucune image selectionnee",
            image="",
            width=72,
            height=8,
        )
        self._preview_tk = None

    def validate(self) -> bool:
        if self.source_path and not Path(self.source_path).is_file():
            mb.showerror("Image invalide", "Le fichier selectionne est introuvable.")
            return False
        return True

    def apply(self) -> None:
        self.result = {
            "source_path": self.source_path,
            "opacity": min(1.0, max(0.05, float(self.opacity_scale.get()) / 100.0)),
            "cleared": bool(self._cleared),
        }
