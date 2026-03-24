from __future__ import annotations

from typing import Any, Callable, Iterable

from monitoring.ui.utils.sortable_tree import make_treeview_sortable


class SearchableSortableTreeMixin:
    """Shared desktop table behavior: column sort + text filter + optional search visibility threshold."""

    search_visibility_threshold: int = 5

    def _init_searchable_sortable_tree(
        self,
        *,
        tree,
        search_var,
        on_query_changed: Callable[[], None],
        search_container=None,
        default_sort_col: str | None = None,
        default_sort_reverse: bool = False,
    ) -> None:
        self.sort_col = default_sort_col
        self.sort_reverse = bool(default_sort_reverse)
        self._search_tree = tree
        self._search_var = search_var
        self._search_on_query_changed = on_query_changed
        self._search_container = search_container
        self._search_container_layout: tuple[str, dict[str, Any]] | None = None
        self._search_container_visible = True

        if search_container is not None:
            manager = str(search_container.winfo_manager() or "").strip()
            if manager == "grid":
                self._search_container_layout = ("grid", dict(search_container.grid_info()))
            elif manager == "pack":
                self._search_container_layout = ("pack", dict(search_container.pack_info()))

        make_treeview_sortable(tree, self)
        search_var.trace_add("write", self._on_shared_search_changed)

    def _on_shared_search_changed(self, *_args) -> None:
        self._search_on_query_changed()

    def _apply_filter_sort(
        self,
        rows: Iterable[Any],
        *,
        searchable_text: Callable[[Any], str],
        sort_value: Callable[[Any, str], Any],
    ) -> list[Any]:
        data = list(rows)
        self._set_search_visible(len(data) >= int(self.search_visibility_threshold))

        query = str(self._search_var.get() or "").strip().lower()
        if query:
            data = [row for row in data if query in str(searchable_text(row) or "").lower()]

        if self.sort_col:
            col = str(self.sort_col)
            reverse = bool(self.sort_reverse)
            try:
                data.sort(key=lambda row: sort_value(row, col), reverse=reverse)
            except Exception:
                pass
        return data

    def _set_search_visible(self, visible: bool) -> None:
        container = getattr(self, "_search_container", None)
        layout = getattr(self, "_search_container_layout", None)
        if container is None or layout is None:
            return
        if bool(getattr(self, "_search_container_visible", True)) == bool(visible):
            return

        manager, options = layout
        if visible:
            if manager == "grid":
                restored = {k: v for k, v in options.items() if k not in {"in"}}
                container.grid(**restored)
            elif manager == "pack":
                restored = {k: v for k, v in options.items() if k not in {"in"}}
                container.pack(**restored)
            self._search_container_visible = True
            return

        if manager == "grid":
            container.grid_remove()
        elif manager == "pack":
            container.pack_forget()
        self._search_container_visible = False
