"""Regression tests for the patched SmartIR custom component.

The tests focus on the things that made ``smartir`` fail to load on current
Home Assistant releases (and therefore made every SmartIR entity show up as
"no longer being provided by the smartir integration"):

* ``distutils.version.StrictVersion`` no longer exists (Python >= 3.12),
* ``hass.components.<domain>`` is deprecated/removed,
* the remaining Home Assistant imports still resolve.
"""
import ast
import importlib
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "smartir"
PY_FILES = sorted(COMPONENT.glob("*.py"))
PLATFORMS = ("climate", "fan", "light", "media_player")


def _trees():
    for path in PY_FILES:
        yield path, ast.parse(path.read_text(encoding="utf-8"))


def test_component_has_expected_files():
    assert PY_FILES, "no python files found in the component"
    assert (COMPONENT / "manifest.json").is_file()


@pytest.mark.parametrize("path", PY_FILES, ids=lambda path: path.name)
def test_no_distutils_imports(path):
    """``distutils`` was removed from the standard library in Python 3.12."""
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            assert not (node.module or "").startswith("distutils"), (
                "%s imports the removed distutils module" % path.name
            )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("distutils"), (
                    "%s imports the removed distutils module" % path.name
                )


def test_no_hass_components_attribute_access():
    """``hass.components`` is deprecated; use ``homeassistant.components``."""
    offenders = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "components"
                and isinstance(node.value, ast.Name)
                and node.value.id == "hass"
            ):
                offenders.append("%s:%s" % (path.name, node.lineno))
    assert not offenders, "deprecated hass.components used at %s" % offenders


def test_version_tuple_ordering():
    module = importlib.import_module("custom_components.smartir")

    assert module._version_tuple("1.18.2") == (1, 18, 2)
    assert module._version_tuple("2026.11.0") > module._version_tuple("2026.10.4")
    assert module._version_tuple("2026.11") == (2026, 11, 0)
    # pre-releases / unknown strings must not raise
    assert module._version_tuple("2026.11.0b3") == (2026, 11, 0)
    assert module._version_tuple("unknown") == (0, 0, 0)
    assert module._version_tuple(None) == (0, 0, 0)


def test_version_check_matches_previous_strict_semantics():
    """``StrictVersion`` comparisons are replaced by tuple comparisons."""
    module = importlib.import_module("custom_components.smartir")

    last_version = "1.18.4"
    assert module._version_tuple(last_version) > module._version_tuple(module.VERSION)

    current = "2026.11.0"
    minimum = "2026.11.0"
    assert not module._version_tuple(current) < module._version_tuple(minimum)
    assert module._version_tuple("2026.10.0") < module._version_tuple(minimum)


def test_integration_module_imports():
    module = importlib.import_module("custom_components.smartir")

    assert module.DOMAIN == "smartir"
    assert callable(module.async_setup)
    assert callable(module._notify)
    assert callable(module._version_tuple)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_platform_modules_import(platform):
    module = importlib.import_module("custom_components.smartir.%s" % platform)

    assert callable(module.async_setup_platform)
    assert callable(module.get_controller)


def test_persistent_notification_helper_uses_component():
    """``_notify`` must go through the persistent_notification component."""
    module = importlib.import_module("custom_components.smartir")
    tree = ast.parse(pathlib.Path(module.__file__).read_text(encoding="utf-8"))

    notify = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_notify"
    )
    calls = [
        node
        for node in ast.walk(notify)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "async_create"
    ]
    assert calls, "_notify does not call persistent_notification.async_create"


REMOVED_HELPER_APIS = (
    "async_track_state_change",
    "async_track_state_added_domain",
    "async_track_state_removed_domain",
)


def test_no_imports_of_removed_home_assistant_apis():
    """Home Assistant 2026.11 no longer exports ``async_track_state_change``.

    SmartIR <= 1.18.0 imported it in climate.py, fan.py and light.py, so those
    platforms raised ImportError during setup and every entity ended up as
    "This entity is no longer being provided by the smartir integration".
    1.18.1 replaced it with ``async_track_state_change_event``; this test keeps
    the old, removed names from coming back.
    """
    offenders = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not (node.module or "").startswith("homeassistant"):
                continue
            for alias in node.names:
                if alias.name in REMOVED_HELPER_APIS:
                    offenders.append(
                        "%s:%s imports %s" % (path.name, node.lineno, alias.name)
                    )
    assert not offenders, offenders
