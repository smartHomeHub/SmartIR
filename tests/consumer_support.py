"""Narrow actual-source consumer harness, not a Home Assistant integration test.

The complete fan/light/media-player class ASTs (and light's closest_match) are
compiled unchanged from the working tree. Imports, platform schemas and setup
are excluded. Entity state publication, feature enums and percentage utilities
are small HA substitutes. Constructors and service methods are real; lifecycle,
restore and sensor callbacks are not exercised. Controllers are the complete
source modules loaded by tests.support, not mocks or extracted implementations.
"""

import ast
import asyncio
import logging
import math
from collections import deque
from enum import IntFlag, StrEnum
from pathlib import Path
from types import SimpleNamespace

from tests.support import load_source

_, controller = load_source()


class Features(IntFlag):
    SET_SPEED = 1
    TURN_OFF = 2
    TURN_ON = 4
    DIRECTION = 8
    OSCILLATE = 16
    PREVIOUS_TRACK = 32
    NEXT_TRACK = 64
    VOLUME_STEP = 128
    VOLUME_MUTE = 256
    SELECT_SOURCE = 512
    PLAY_MEDIA = 1024


class ColorMode(StrEnum):
    UNKNOWN = "unknown"
    COLOR_TEMP = "color_temp"
    BRIGHTNESS = "brightness"
    ONOFF = "onoff"


def snapshot(entity):
    if hasattr(entity, "_speed"):
        return (entity._speed, entity._last_on_speed, entity._on_by_remote)
    if hasattr(entity, "_power"):
        return (entity._power, entity._brightness, entity._colortemp)
    return (entity._state, entity._source)


class Entity:
    def async_write_ha_state(self):
        self.hass.writes.append(snapshot(self))


class RestoreEntity:
    pass


def load_consumer(platform, class_name):
    """Execute real class bodies with explicit, minimal HA boundary globals."""
    path = (Path(__file__).resolve().parents[1] / "custom_components"
            / "smartir" / f"{platform}.py")
    source = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    namespace = {
        "__name__": f"smartir_consumer_test.{platform}",
        "asyncio": asyncio,
        "_LOGGER": logging.getLogger(f"smartir_consumer_test.{platform}"),
        "FanEntity": Entity, "LightEntity": Entity, "MediaPlayerEntity": Entity,
        "RestoreEntity": RestoreEntity,
        "FanEntityFeature": Features, "MediaPlayerEntityFeature": Features,
        "ColorMode": ColorMode, "MediaType": SimpleNamespace(CHANNEL="channel"),
        "STATE_ON": "on", "STATE_OFF": "off", "STATE_UNKNOWN": "unknown",
        "CONF_NAME": "name",
        "ATTR_BRIGHTNESS": "brightness",
        "ATTR_COLOR_TEMP_KELVIN": "color_temp_kelvin",
        "DIRECTION_REVERSE": "reverse", "DIRECTION_FORWARD": "forward",
        "Event": dict, "EventStateChangedData": dict,
        "callback": lambda function: function,
        "get_controller": controller.get_controller,
        "ordered_list_item_to_percentage":
            lambda items, item: int((items.index(item) + 1) * 100 / len(items)),
        "percentage_to_ordered_list_item":
            lambda items, percent: items[math.ceil(percent * len(items) / 100) - 1],
    }
    selected = []
    for node in source.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Constant):
                    namespace[target.id] = ast.literal_eval(node.value)
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            selected.append(node)
        if isinstance(node, ast.FunctionDef) and node.name == "closest_match":
            selected.append(node)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"),
         namespace)
    return namespace[class_name]


Fan = load_consumer("fan", "SmartIRFan")
Light = load_consumer("light", "SmartIRLight")
MediaPlayer = load_consumer("media_player", "SmartIRMediaPlayer")


class Services:
    """Record submission/completion separately and gate actual awaited calls."""

    def __init__(self):
        self.calls = []
        self.started = asyncio.Queue()
        self.outcomes = deque()
        self.pending = []
        self.active = 0
        self.max_active = 0

    async def async_call(self, domain, service, data, blocking=False):
        call = SimpleNamespace(domain=domain, service=service, data=data,
                               blocking=blocking, completed=False,
                               cancelled=False, error=None)
        self.calls.append(call)
        self.started.put_nowait(call)
        outcome = self.outcomes.popleft() if self.outcomes else None

        async def complete():
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            try:
                if isinstance(outcome, asyncio.Future):
                    await outcome
                elif isinstance(outcome, Exception):
                    raise outcome
                call.completed = True
            except asyncio.CancelledError:
                call.cancelled = True
                raise
            except Exception as error:
                call.error = error
                raise
            finally:
                self.active -= 1

        if blocking:
            await complete()
        else:
            self.pending.append(asyncio.create_task(complete()))
