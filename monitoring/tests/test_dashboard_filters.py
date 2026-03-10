from types import SimpleNamespace

from monitoring.ui.dashboard_detail_mixin import DashboardDetailMixin
from monitoring.ui.device_list_view import DeviceListView


class _FakeTree:
    def __init__(self):
        self.items = {}
        self.detached = set()

    def winfo_exists(self):
        return True

    def exists(self, iid):
        return iid in self.items

    def insert(self, _parent, _index, iid, image=None, values=(), tags=()):
        self.items[iid] = {"image": image, "values": values, "tags": tags}
        self.detached.discard(iid)

    def item(self, iid, image=None, values=None, tags=None):
        row = self.items[iid]
        if image is not None:
            row["image"] = image
        if values is not None:
            row["values"] = values
        if tags is not None:
            row["tags"] = tags

    def delete(self, *iids):
        for iid in iids:
            self.items.pop(iid, None)
            self.detached.discard(iid)

    def move(self, iid, _parent, _index):
        self.detached.discard(iid)

    def reattach(self, iid, _parent, _index):
        self.detached.discard(iid)

    def detach(self, iid):
        self.detached.add(iid)

    def config(self, **_kwargs):
        return None


def test_device_list_update_display_reattaches_existing_rows():
    tree = _FakeTree()
    tree.insert("", "end", iid="srv1", values=("SRV1", "1.1.1.1", "desc"), tags=("online",))
    tree.detach("srv1")

    fake = SimpleNamespace(
        tree=tree,
        controller=SimpleNamespace(unregister_view=lambda _view: None),
        refresh_paused=False,
        is_locked_view=lambda: False,
        winfo_exists=lambda: True,
        model=SimpleNamespace(
            device_data={
                "server": {
                    "srv1": SimpleNamespace(name="SRV1", ip="1.1.1.1", description="desc", status="offline")
                }
            },
            do_run={"server": True},
            type_definitions={"server": {"label": "Serveur"}},
        ),
        device_type="server",
        columns=("name", "ip", "desc"),
        sort_col=None,
        sort_reverse=False,
        _row_state={"srv1": ("online", ("SRV1", "1.1.1.1", "desc"))},
        _rendered_iids=set(),
        search_var=SimpleNamespace(get=lambda: ""),
        btn_toggle=SimpleNamespace(config=lambda **_kwargs: None),
        theme=SimpleNamespace(
            colors={
                "button_active_bg": "#0f0",
                "button_inactive_bg": "#f00",
                "button_active_fg": "#fff",
                "button_inactive_fg": "#000",
            }
        ),
        force_inventory_visible=False,
        _set_placeholder_visible=lambda *_args, **_kwargs: None,
        img_online=object(),
        img_offline=object(),
        img_idle=object(),
    )

    DeviceListView.update_display(fake)

    assert "srv1" not in tree.detached
    assert tree.items["srv1"]["tags"] == ("offline",)


def test_dashboard_filter_reset_reattaches_all_rows():
    server_tree = _FakeTree()
    global_tree = _FakeTree()
    server_tree.insert("", "end", iid="srv1")
    global_tree.insert("", "end", iid="server::srv1")
    server_tree.detach("srv1")
    global_tree.detach("server::srv1")

    fake = SimpleNamespace(
        active_tree_filter=None,
        type_views={"server": SimpleNamespace(tree=server_tree)},
        consolidated_app=SimpleNamespace(tree=global_tree),
        model=SimpleNamespace(device_data={"server": {"srv1": SimpleNamespace(status="offline")}}),
    )
    fake._filter_tree = DashboardDetailMixin._filter_tree
    fake._filter_consolidated_tree = DashboardDetailMixin._filter_consolidated_tree

    DashboardDetailMixin._apply_active_tree_filter(fake)

    assert "srv1" not in server_tree.detached
    assert "server::srv1" not in global_tree.detached
