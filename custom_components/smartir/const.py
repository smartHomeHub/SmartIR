from __future__ import annotations

DOMAIN = "smartir"
VERSION = "1.19.0-ui"

CONF_PLATFORM = "platform"
CONF_UNIQUE_ID = "unique_id"
CONF_DEVICE_CODE = "device_code"
CONF_CONTROLLER_DATA = "controller_data"
CONF_DELAY = "delay"
CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_POWER_SENSOR = "power_sensor"
CONF_POWER_SENSOR_RESTORE_STATE = "power_sensor_restore_state"
CONF_SOURCE_NAMES = "source_names"
CONF_DEVICE_CLASS = "device_class"

CONF_CHECK_UPDATES = "check_updates"
CONF_UPDATE_BRANCH = "update_branch"

DEFAULT_DELAY = 0.5
DEFAULT_DEVICE_CLASS = "tv"
PLATFORMS = ["climate", "fan", "light", "media_player"]
PLATFORM_TITLES = {
    "climate": "Climate",
    "fan": "Fan",
    "light": "Light",
    "media_player": "Media Player",
}
