from pathlib import Path

from monitoring.utils.file_drop import decode_dropped_paths


def test_decode_dropped_paths_handles_windows_braced_list(tmp_path: Path) -> None:
    first = tmp_path / "switch core.cfg"
    second = tmp_path / "edge.conf"
    first.write_text("a")
    second.write_text("b")
    raw = f"{{{first}}} {{{second}}}"
    paths = decode_dropped_paths([raw])
    assert paths == [first, second]


def test_decode_dropped_paths_handles_nul_separated_bytes(tmp_path: Path) -> None:
    first = tmp_path / "one.cfg"
    second = tmp_path / "two.cfg"
    first.write_text("1")
    second.write_text("2")
    raw = f"{first}\x00{second}\x00".encode("utf-8")
    paths = decode_dropped_paths([raw])
    assert paths == [first, second]
