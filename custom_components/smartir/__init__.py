"""The SmartIR component."""

import logging
import os.path
import json
import numpy

_LOGGER = logging.getLogger(__name__)


class DeviceData:
    @staticmethod
    async def load_file(device_code, device_class, check_data, hass):
        """Load device JSON file."""
        device_json_file_name = str(device_code) + ".json"

        device_files_subdir = os.path.join("custom_codes", device_class)
        device_files_absdir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), device_files_subdir
        )
        if os.path.isdir(device_files_absdir):
            device_json_file_path = os.path.join(
                device_files_absdir, device_json_file_name
            )
            if os.path.exists(device_json_file_path):
                _LOGGER.debug(
                    "Loading custom device Json file '%s'.", device_json_file_name
                )
                if device_data := await DeviceData.check_file(
                    device_json_file_name,
                    device_json_file_path,
                    device_class,
                    check_data,
                    hass,
                ):
                    return device_data
        else:
            os.makedirs(device_files_absdir)

        device_files_subdir = os.path.join("codes", device_class)
        device_files_absdir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), device_files_subdir
        )
        if os.path.isdir(device_files_absdir):
            device_json_file_path = os.path.join(
                device_files_absdir, device_json_file_name
            )
            if os.path.exists(device_json_file_path):
                _LOGGER.debug("Loading device Json file '%s'.", device_json_file_name)
                if device_data := await DeviceData.check_file(
                    device_json_file_name,
                    device_json_file_path,
                    device_class,
                    check_data,
                    hass,
                ):
                    return device_data
            else:
                _LOGGER.error(
                    "Device Json file '%s' doesn't exists!", device_json_file_name
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
        with open(file_path, "r") as file:
            try:
                _LOGGER.debug("Loading device JSON file '%s'.", file_path)
                data = json.load(file)
                _LOGGER.debug("Loaded device JSON file '%s'.", file_path)
                return data
            except Exception as e:
                _LOGGER.error(
                    "Error opening device JSON file '%s': '%s'.", file_path, e
                )
                return None

    @staticmethod
    async def check_file(file_name, file_path, device_class, check_data, hass):
        device_data = await hass.async_add_executor_job(
            DeviceData.read_file_as_json, file_path
        )

        if not isinstance(device_data, dict):
            _LOGGER.error(
                "Invalid device JSON file '%s': invalid JSON format.", file_name
            )
            return None

        if not (
            "manufacturer" in device_data
            and isinstance(device_data["manufacturer"], str)
            and device_data["manufacturer"]
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'manufacturer'.",
                file_name,
            )
            return False

        if not (
            "supportedModels" in device_data
            and isinstance(device_data["supportedModels"], list)
            and len(device_data["supportedModels"])
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'supportedModels'.",
                file_name,
            )
            return False

        if not (
            "supportedController" in device_data
            and isinstance(device_data["supportedController"], str)
            and device_data["supportedController"]
            in check_data["controller_support"].keys()
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'supportedController'.",
                file_name,
            )
            return False

        if not (
            "commandsEncoding" in device_data
            and isinstance(device_data["commandsEncoding"], str)
            and device_data["commandsEncoding"]
            in check_data["controller_support"][device_data["supportedController"]]
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'commandsEncoding'.",
                file_name,
            )
            return False

        if device_class == "climate":
            if not DeviceData.check_file_climate(file_name, device_data, check_data):
                return False
        elif device_class == "fan":
            if not DeviceData.check_file_fan(file_name, device_data, check_data):
                return False
        elif device_class == "media_player":
            if not DeviceData.check_file_media_player(
                file_name, device_data, check_data
            ):
                return False
        return device_data

    @staticmethod
    def check_file_climate(file_name, device_data, check_data):
        modes_used = {}

        if not (
            "operationModes" in device_data
            and isinstance(device_data["operationModes"], list)
            and len(device_data["operationModes"])
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'operationModes'.",
                file_name,
            )
            return False

        modes_list = ["operation"]
        modes_used["operation"] = {}
        for mode in device_data["operationModes"]:
            if not (isinstance(mode, str) and mode in check_data["hvac_modes"]):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'operationModes' value '%s'.",
                    file_name,
                    mode,
                )
                return False
            modes_used["operation"][mode] = 0
        for level in ["preset", "fan", "swing"]:
            attr = level + "Modes"
            if attr in device_data and isinstance(device_data[attr], list):
                modes_list.append(level)
                modes_used[level] = {}
                if len(device_data[attr]):
                    for mode in device_data[attr]:
                        if not (isinstance(mode, str)):
                            _LOGGER.error(
                                "Invalid device JSON file '%s': invalid attribute '%s' value '%s'.",
                                file_name,
                                attr,
                                mode,
                            )
                            return False
                        modes_used[level][mode] = 0

        if not (
            "temperatureUnit" in device_data
            and isinstance(device_data["temperatureUnit"], str)
            and device_data["temperatureUnit"] in ["C", "F", "K"]
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'temperatureUnit'.",
                file_name,
            )
            return False

        if not (
            "precision" in device_data
            and isinstance(device_data["precision"], int)
            or isinstance(device_data["precision"], float)
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'precison'.",
                file_name,
            )
            return False
        if not (
            "minTemperature" in device_data
            and isinstance(device_data["minTemperature"], int)
            or isinstance(device_data["minTemperature"], float)
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'minTemperature'.",
                file_name,
            )
            return False
        if not (
            "maxTemperature" in device_data
            and isinstance(device_data["maxTemperature"], int)
            or isinstance(device_data["maxTemperature"], float)
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'maxTemperature'.",
                file_name,
            )
            return False

        modes_list.append("temperature")
        modes_used["temperature"] = {}
        if device_data["precision"] == 1:
            if round(float(device_data["minTemperature"])) != float(
                device_data["minTemperature"]
            ):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'minTemperature'.",
                    file_name,
                )
                return False
            if round(float(device_data["maxTemperature"])) != float(
                device_data["maxTemperature"]
            ):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'maxTemperature'.",
                    file_name,
                )
                return False
        elif device_data["precision"] == 0.5:
            if round((float(device_data["minTemperature"]) * 2) / 2.0, 1) != float(
                device_data["minTemperature"]
            ):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'minTemperature'.",
                    file_name,
                )
                return False
            if round((float(device_data["maxTemperature"]) * 2) / 2.0, 1) != float(
                device_data["maxTemperature"]
            ):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'maxTemperature'.",
                    file_name,
                )
                return False
        elif device_data["precision"] == 0.1:
            if round(float(device_data["minTemperature"]), 1) != float(
                device_data["minTemperature"]
            ):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'minTemperature'.",
                    file_name,
                )
                return False
            if round(float(device_data["maxTemperature"]), 1) != float(
                device_data["maxTemperature"]
            ):
                _LOGGER.error(
                    "Invalid device JSON file '%s': invalid attribute 'maxTemperature'.",
                    file_name,
                )
                return False
        else:
            _LOGGER.error(
                "Invalid device JSON file '%s': invalid attribute 'precison'.",
                file_name,
            )
            return False

        check_data["precision"] = device_data["precision"]

        modes_list.append("temperature")
        modes_used["temperature"] = {}
        for temp in numpy.arange(
            device_data["minTemperature"],
            device_data["maxTemperature"] + device_data["precision"],
            device_data["precision"],
        ):
            modes_used["temperature"].setdefault(temp, 0)

        if "commands" not in device_data:
            _LOGGER.error(
                "Invalid device JSON file '%s': missing attribute 'commands'.",
                file_name,
            )
            return False

        return DeviceData.check_file_climate_commands(
            file_name,
            0,
            "",
            modes_list,
            modes_used,
            check_data,
            device_data["commands"],
        )

    def check_file_climate_commands(
        file_name, depth, path, modes_list, modes_used, check_data, commands
    ):
        level = modes_list[depth]
        path += "->" + level

        if not (isinstance(commands, dict) and len(commands)):
            _LOGGER.error(
                "Invalid device JSON file '%s':  missing '%s' mode command.",
                file_name,
                path,
            )
            return False
        elif level == "operation":
            check = []
            # operation modes level
            if "off" in commands:
                if not (isinstance(commands["off"], str) and commands["off"]):
                    _LOGGER.error(
                        "Invalid device JSON file '%s': missing or invalid 'off' operation mode command.",
                        file_name,
                    )
                    return False
                check.append("off")
            else:
                for mode in modes_used[level]:
                    off_mode = "off_" + mode
                    if not (
                        off_mode in commands
                        and isinstance(commands[off_mode], str)
                        and commands[off_mode]
                    ):
                        _LOGGER.error(
                            "Invalid device JSON file '%s': missing or invalid '%s' operation mode command.",
                            file_name,
                            off_mode,
                        )
                        return False
                    check.append(off_mode)
            for mode in modes_used[level]:
                if not mode in commands:
                    _LOGGER.error(
                        "Invalid device JSON file '%s': missing '%s' operation mode command.",
                        file_name,
                        mode,
                    )
                    return False
                elif not DeviceData.check_file_climate_commands(
                    file_name,
                    depth + 1,
                    path + "(" + mode + ")",
                    modes_list,
                    modes_used,
                    check_data,
                    commands[mode],
                ):
                    return False
                check.append(mode)

            # check for non valid operational modes in commands
            if not set(commands.keys()).issubset(set(check)):
                _LOGGER.error(
                    "Invalid device JSON file '%s': operation mode '%s' command command.",
                    file_name,
                    mode,
                )
                return False

            # check for missing commands for declared modes and temperatures
            for level in modes_used:
                for attr in modes_used[level]:
                    if attr == 0:
                        _LOGGER.error(
                            "Invalid device JSON file '%s': '%s' '%s' is defined, but is not used / command is missing.",
                            file_name,
                            level,
                            attr,
                        )
                        return False

        else:
            if "-" in commands:
                if len(commands) != 1:
                    _LOGGER.error(
                        "Invalid device JSON file '%s': command '%s' key '-' can't be combined with any named modes.",
                        file_name,
                        path,
                    )
                    return False
            elif level == "temperature":
                for temp in commands.keys():
                    if not (isinstance(commands[temp], str) and commands[temp]):
                        return False

                    try:
                        if check_data["precision"] == 0.5:
                            temp = round((float(temp) * 2) / 2.0, 1)
                        elif check_data["precision"] == 0.1:
                            temp = round(float(temp), 1)
                        else:
                            temp = round(float(temp))

                    except ValueError:
                        _LOGGER.error(
                            "Invalid device JSON file '%s': command '%s': invalid key '%s' temperature command.",
                            file_name,
                            path,
                            temp,
                        )
                        return False

                    if temp not in modes_used[level].keys():
                        _LOGGER.error(
                            "Invalid device JSON file '%s': command '%s': missing '%s' temperature command.",
                            file_name,
                            path,
                            temp,
                        )
                        return False
                    modes_used[level][temp] += 1
            else:
                for mode in commands.keys():
                    if mode not in modes_used[level].keys():
                        _LOGGER.error(
                            "Invalid device JSON file '%s': command '%s': missing '%s' mode command.",
                            file_name,
                            path,
                            mode,
                        )
                        return False
                    elif not DeviceData.check_file_climate_commands(
                        file_name,
                        depth + 1,
                        path + "(" + mode + ")",
                        modes_list,
                        modes_used,
                        check_data,
                        commands[mode],
                    ):
                        return False
                    modes_used[level][mode] += 1

        return True

    @staticmethod
    def check_file_fan(file_name, device_data, check_data):
        if not (
            "speed" in device_data
            and isinstance(device_data["speed"], list)
            and len(device_data["speed"])
        ):
            _LOGGER.error(
                "Invalid device JSON file '%s': missing or invalid attribute 'speed'.",
                file_name,
            )
            return False
        return True

    @staticmethod
    def check_file_media_player(file_name, device_data, check_data):
        return True
