from __future__ import annotations

import os
from pathlib import Path
from tkinter import PhotoImage, messagebox

from monitoring.config.settings import save_settings
from monitoring.ui.dialogs.watermark_settings import WatermarkSettingsDialog


class DashboardWatermarkMixin:
    def _custom_watermark_target_path(self) -> Path:
        app_data_root = os.environ.get("LOCALAPPDATA") or str(Path.home())
        target_dir = Path(app_data_root) / "NetworkMonitoringProject" / "assets"
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / "custom_watermark.png"

    def _materialize_watermark(self, source_path: str, opacity: float, *, source_baseline_opacity: float = 1.0) -> str:
        src = Path(source_path)
        if not source_path or not src.is_file():
            return ""
        target = self._custom_watermark_target_path()
        try:
            from PIL import Image, ImageEnhance  # type: ignore
        except Exception:
            raise RuntimeError("Pillow est requis pour appliquer l'opacite du watermark.")

        img = Image.open(src).convert("RGBA")
        img.thumbnail((360, 220), Image.Resampling.LANCZOS)
        alpha = img.split()[-1]
        target_opacity = min(1.0, max(0.05, float(opacity or 0.16)))
        baseline_opacity = min(1.0, max(0.05, float(source_baseline_opacity or 1.0)))
        factor = target_opacity / baseline_opacity
        alpha = ImageEnhance.Brightness(alpha).enhance(factor)
        img.putalpha(alpha)
        img.save(target, format="PNG")
        return str(target)

    def _open_watermark_dialog(self) -> None:
        dlg = WatermarkSettingsDialog(
            self.root,
            current_source_path=str(getattr(self.notification_settings, "watermark_source_path", "") or ""),
            current_rendered_path=str(getattr(self.notification_settings, "watermark_image_path", "") or ""),
            current_opacity=float(getattr(self.notification_settings, "watermark_opacity", 0.16) or 0.16),
        )
        if dlg.result is None:
            return

        source_path = str(dlg.result.get("source_path", "") or "").strip()
        opacity = min(1.0, max(0.05, float(dlg.result.get("opacity", 0.16) or 0.16)))
        cleared = bool(dlg.result.get("cleared", False))
        current_rendered = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()
        current_saved_opacity = float(getattr(self.notification_settings, "watermark_opacity", 0.16) or 0.16)
        if cleared:
            self.notification_settings.watermark_source_path = ""
            self.notification_settings.watermark_image_path = ""
            self.notification_settings.watermark_opacity = opacity
            save_settings(self.notification_settings)
            self._refresh_watermarks()
            return

        if not source_path:
            source_path = str(getattr(self.notification_settings, "watermark_source_path", "") or "").strip()
        if not source_path:
            source_path = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()

        try:
            baseline = 1.0
            try:
                if source_path and current_rendered and Path(source_path).resolve() == Path(current_rendered).resolve():
                    baseline = min(1.0, max(0.05, current_saved_opacity))
            except Exception:
                baseline = 1.0

            processed_path = self._materialize_watermark(source_path, opacity, source_baseline_opacity=baseline)
            _img_check = PhotoImage(file=processed_path)
            del _img_check
        except Exception as exc:
            messagebox.showerror(
                "Personnalisation",
                f"Impossible d'appliquer l'image de fond: {exc}",
            )
            return

        try:
            same_as_generated = bool(current_rendered) and Path(source_path).resolve() == Path(current_rendered).resolve()
        except Exception:
            same_as_generated = False
        self.notification_settings.watermark_source_path = "" if same_as_generated else source_path
        self.notification_settings.watermark_image_path = processed_path
        self.notification_settings.watermark_opacity = opacity
        save_settings(self.notification_settings)
        self._refresh_watermarks()

    def _refresh_dashboard_watermark(self) -> None:
        custom_path = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()
        selected = custom_path if custom_path and Path(custom_path).is_file() else ""

        if selected:
            try:
                self._dashboard_watermark = PhotoImage(file=selected)
            except Exception:
                self._dashboard_watermark = None
        else:
            self._dashboard_watermark = None
        self.placeholder_image.configure(image=self._dashboard_watermark)
        self.placeholder_image.image = self._dashboard_watermark
        if self._dashboard_watermark is None:
            self.placeholder_image.pack_forget()
        elif not self.placeholder_image.winfo_manager():
            self.placeholder_image.pack(pady=(24, 8))

    def _refresh_watermarks(self) -> None:
        self._refresh_dashboard_watermark()
        custom_path = str(getattr(self.notification_settings, "watermark_image_path", "") or "").strip()
        for view in [*getattr(self, "type_views", {}).values(), getattr(self, "consolidated_app", None)]:
            if view is None:
                continue
            try:
                view.refresh_watermark_image(custom_path)
            except Exception:
                continue

