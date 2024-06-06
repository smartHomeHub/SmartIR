"""The SmartIR component."""

import logging
import os.path
import json

_LOGGER = logging.getLogger(__name__)


class DeviceData:
    @staticmethod
    async def load_file(device_code, device_class, required_keys, hass):
        """Load device JSON file."""
        device_json_filename = str(device_code) + ".json"

        device_files_subdir = os.path.join("custom_codes", device_class)
        device_files_absdir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), device_files_subdir
        )
        if os.path.isdir(device_files_absdir):
            device_json_path = os.path.join(device_files_absdir, device_json_filename)
            if os.path.exists(device_json_path):
                _LOGGER.debug(
                    "Loading custom device Json file '%s'.", device_json_filename
                )
                if device_data := await DeviceData.check_file(
                    device_json_filename, device_json_path, required_keys, hass
                ):
                    return device_data
        else:
            os.makedirs(device_files_absdir)

        device_files_subdir = os.path.join("codes", device_class)
        device_files_absdir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), device_files_subdir
        )
        if os.path.isdir(device_files_absdir):
            device_json_path = os.path.join(device_files_absdir, device_json_filename)
            if os.path.exists(device_json_path):
                _LOGGER.debug("Loading device Json file '%s'.", device_json_filename)
                if device_data := await DeviceData.check_file(
                    device_json_filename, device_json_path, required_keys, hass
                ):
                    return device_data
            else:
                _LOGGER.error(
                    "Device Json file '%s' doesn't exists!", device_json_filename
                )
                return None
        else:
            _LOGGER.error(
                "Devices Json files directory '%s' doesn't exists!", device_files_absdir
            )
            return None

        return None

    @staticmethod
    def read_file_as_json(file_path: str) -> dict:
        """Read a JSON file and return its content as a dictionary."""
        with open(file_path, 'r') as file:
            try:
                _LOGGER.debug(f"Loading JSON file {file_path}")
                data = json.load(file)
                _LOGGER.debug(f"{file_path} file loaded")
                return data
            except Exception as e:
                _LOGGER.error(f"The device JSON file is invalid: {e}")
                return None

    @staticmethod
    async def check_file(device_json_filename, device_json_path, required_keys, hass):
        device_data = await hass.async_add_executor_job(
            DeviceData.read_file_as_json, device_json_path
        )

        if not isinstance(device_data, dict):
            _LOGGER.error("Invalid device code file '%s.", device_json_filename)
            return None

        for key in required_keys:
            if not (key in device_data and device_data[key]):
                _LOGGER.error(
                    "Invalid device JSON file '%s', missing or not defined '%s'!",
                    device_json_filename,
                    key,
                )
                return None

        if not (
            "commands" in device_data
            and isinstance(device_data["commands"], dict)
            and len(device_data["commands"])
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s', missing 'commands'!",
                device_json_filename,
            )
            return None

        return device_data
