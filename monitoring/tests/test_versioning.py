from __future__ import annotations

from monitoring.versioning import _extract_branch_version, resolve_display_version


def test_extract_branch_version_for_prerelease_branch():
    assert _extract_branch_version("pre-release/0.9") == "0.9"
    assert _extract_branch_version("pre-release/1.0.9") == "1.0.9"
    assert _extract_branch_version("prerelease/2.3.4") == "2.3.4"


def test_extract_branch_version_ignores_non_matching_branch():
    assert _extract_branch_version("feature/x") == ""
    assert _extract_branch_version("release/1.0.9") == ""


def test_resolve_display_version_prefers_prerelease_branch_version():
    assert resolve_display_version("0.8-pre-release", "pre-release/0.9") == "0.9-pre-release"


def test_resolve_display_version_fallbacks_to_base_version():
    assert resolve_display_version("0.9-pre-release", "feature/new-ui") == "0.9-pre-release"
