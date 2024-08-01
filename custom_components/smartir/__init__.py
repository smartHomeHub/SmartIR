"""The SmartIR component."""

import logging
import os.path
import hashlib
import json

from .controller_const import CONTROLLER_SUPPORT

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
                    "Loading custom %s device JSON file '%s'.",
                    device_class,
                    device_json_file_name,
                )
                device_data = await hass.async_add_executor_job(
                    DeviceData.read_file_as_json, device_json_file_path
                )
                if await DeviceData.check_file(
                    device_json_file_name,
                    device_data,
                    device_class,
                    check_data,
                ):
                    return device_data
                else:
                    return None
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
                _LOGGER.debug(
                    "Loading %s device JSON file '%s'.",
                    device_class,
                    device_json_file_name,
                )
                device_data = await hass.async_add_executor_job(
                    DeviceData.read_file_as_json, device_json_file_path
                )
                if await DeviceData.check_file(
                    device_json_file_name,
                    device_data,
                    device_class,
                    check_data,
                ):
                    return device_data
                else:
                    return None
            else:
                _LOGGER.error(
                    "Device JSON file '%s' doesn't exists!", device_json_file_name
                )
        else:
            _LOGGER.error(
                "Devices JSON files directory '%s' doesn't exists!", device_files_absdir
            )

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
    async def check_file(file_name, device_data, device_class, check_data):
        if not isinstance(device_data, dict):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': invalid JSON format.",
                device_class,
                file_name,
            )
            return None

        if not (
            "manufacturer" in device_data
            and isinstance(device_data["manufacturer"], str)
            and device_data["manufacturer"]
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'manufacturer'.",
                device_class,
                file_name,
            )
            return False

        if not (
            "supportedModels" in device_data
            and isinstance(device_data["supportedModels"], list)
            and len(device_data["supportedModels"])
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'supportedModels'.",
                device_class,
                file_name,
            )
            return False

        if not (
            "supportedController" in device_data
            and isinstance(device_data["supportedController"], str)
            and device_data["supportedController"] in CONTROLLER_SUPPORT.keys()
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'supportedController'.",
                device_class,
                file_name,
            )
            return False

        if not (
            "commandsEncoding" in device_data
            and isinstance(device_data["commandsEncoding"], str)
            and device_data["commandsEncoding"]
            in CONTROLLER_SUPPORT[device_data["supportedController"]]
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'commandsEncoding'.",
                device_class,
                file_name,
            )
            return False

        if device_class == "climate":
            if DeviceData.check_file_climate(
                file_name, device_data, device_class, check_data
            ):
                return True
        elif device_class == "fan":
            if DeviceData.check_file_fan(
                file_name, device_data, device_class, check_data
            ):
                return True
        elif device_class == "media_player":
            if DeviceData.check_file_media_player(
                file_name, device_data, device_class, check_data
            ):
                return True
        return False

    @staticmethod
    def check_file_climate(file_name, device_data, device_class, check_data):
        modes_used = {}
        commands_used = {}

        if not (
            "operationModes" in device_data
            and isinstance(device_data["operationModes"], list)
            and len(device_data["operationModes"])
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'operationModes'.",
                device_class,
                file_name,
            )
            return False

        modes_list = ["operation"]
        modes_used["operation"] = {}
        for mode in device_data["operationModes"]:
            if not (isinstance(mode, str) and mode in check_data["hvac_modes"]):
                _LOGGER.error(
                    "Invalid %s device JSON file '%s': invalid attribute 'operationModes' value '%s'.",
                    device_class,
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
                                "Invalid %s device JSON file '%s': invalid attribute '%s' value '%s'.",
                                device_class,
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
                "Invalid %s device JSON file '%s': missing or invalid attribute 'temperatureUnit'.",
                device_class,
                file_name,
            )
            return False

        if not (
            "precision" in device_data
            and (
                isinstance(device_data["precision"], int)
                or isinstance(device_data["precision"], float)
            )
            and device_data["precision"] in [0.1, 0.5, 1, 2]
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'precison'.",
                device_class,
                file_name,
            )
            return False
        check_data["precision"] = device_data["precision"]

        if not (
            "minTemperature" in device_data
            and (
                isinstance(device_data["minTemperature"], int)
                or isinstance(device_data["minTemperature"], float)
            )
            and DeviceData.precision_round(
                device_data["minTemperature"], device_data["precision"]
            )
            == float(device_data["minTemperature"])
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'minTemperature'.",
                device_class,
                file_name,
            )
            return False

        if not (
            "maxTemperature" in device_data
            and (
                isinstance(device_data["maxTemperature"], int)
                or isinstance(device_data["maxTemperature"], float)
            )
            and DeviceData.precision_round(
                device_data["maxTemperature"], device_data["precision"]
            )
            == float(device_data["maxTemperature"])
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'maxTemperature'.",
                device_class,
                file_name,
            )
            return False

        modes_list.append("temperature")
        modes_used["temperature"] = {}
        temp_list = [device_data["minTemperature"]]
        while temp_list[-1] <= device_data["maxTemperature"]:
            temp_list.append(
                DeviceData.precision_round(
                    temp_list[-1] + device_data["precision"], device_data["precision"]
                )
            )
        for temp in temp_list:
            modes_used["temperature"].setdefault(temp, 0)

        if "commands" not in device_data:
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing attribute 'commands'.",
                device_class,
                file_name,
            )
            return False

        results = DeviceData.check_file_climate_commands(
            file_name,
            0,
            modes_list,
            modes_used,
            commands_used,
            device_class,
            check_data,
            device_data["commands"],
        )

        # check if same IR command were find in the ddevice data
        if list(filter(lambda key: commands_used[key] > 1, commands_used.keys())):
            _LOGGER.info(
                "Invalid %s device JSON file '%s': duplicated commands detected.",
                device_class,
                file_name,
            )

        return results

    @staticmethod
    def check_file_climate_commands(
        file_name,
        depth,
        modes_list,
        modes_used,
        commands_used,
        device_class,
        check_data,
        commands,
    ):
        level = modes_list[depth]

        if not (isinstance(commands, dict) and len(commands)):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': invalid format at %s level.",
                device_class,
                file_name,
                level,
            )
            return False
        elif level == "operation":
            check = []
            # operation modes level
            if "on" in commands:
                if not (isinstance(commands["on"], str) and commands["on"]):
                    _LOGGER.error(
                        "Invalid %s device JSON file '%s': missing or invalid 'on' operation mode command.",
                        device_class,
                        file_name,
                    )
                    return False
                check.append("on")
            if "off" in commands:
                if not (isinstance(commands["off"], str) and commands["off"]):
                    _LOGGER.error(
                        "Invalid %s device JSON file '%s': missing or invalid 'off' operation mode command.",
                        device_class,
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
                            "Invalid %s device JSON file '%s': missing or invalid 'off' or '%s' operation mode command.",
                            device_class,
                            file_name,
                            off_mode,
                        )
                        return False
                    check.append(off_mode)
            for mode in modes_used[level]:
                if not mode in commands:
                    _LOGGER.error(
                        "Invalid %s device JSON file '%s': not defined operation mode '%s' command key used. %s",
                        device_class,
                        file_name,
                        mode,
                        commands.keys(),
                    )
                    return False
                elif not DeviceData.check_file_climate_commands(
                    file_name,
                    depth + 1,
                    modes_list,
                    modes_used,
                    commands_used,
                    device_class,
                    check_data,
                    commands[mode],
                ):
                    return False
                check.append(mode)

            # check for non defined operational modes in commands
            invalid = [mode for mode in commands.keys() if mode not in check]
            if invalid:
                _LOGGER.error(
                    "Invalid %s device JSON file '%s': operation mode '%s' is not defined, but it is used in commands.",
                    device_class,
                    file_name,
                    invalid[0],
                )
                return False

            # check for missing commands for declared modes and temperatures
            for level in modes_used:
                for attr in modes_used[level]:
                    if attr == 0:
                        _LOGGER.error(
                            "Invalid %s device JSON file '%s': '%s' '%s' is defined, but not used in commands.",
                            device_class,
                            file_name,
                            level,
                            attr,
                        )
                        return False

        else:
            if "-" in commands:
                if len(commands) != 1:
                    _LOGGER.error(
                        "Invalid %s device JSON file '%s': command '%s' mode key '-' can't be combined with any named modes.",
                        device_class,
                        file_name,
                        level,
                    )
                    return False
            elif level == "temperature":
                for temp in commands.keys():
                    if not (isinstance(commands[temp], str) and commands[temp]):
                        _LOGGER.error(
                            "Invalid %s device JSON file '%s': invalid 'temperature' '%s' command value '%s'.",
                            device_class,
                            file_name,
                            temp,
                            commands[temp],
                        )
                        return False

                    string = commands[temp]
                    result = hashlib.md5(string.encode())
                    hash = result.hexdigest()
                    if hash in commands_used:
                        _LOGGER.debug(
                            "Invalid %s device JSON file '%s': 'temperature' '%s' command '%s' already used.",
                            device_class,
                            file_name,
                            temp,
                            commands[temp],
                        )
                        commands_used[hash] += 1
                    else:
                        commands_used[hash] = 1

                    try:
                        temp = DeviceData.precision_round(temp, check_data["precision"])
                    except ValueError:
                        _LOGGER.error(
                            "Invalid %s device JSON file '%s': invalid 'temperature' command key '%s' value.",
                            device_class,
                            file_name,
                            temp,
                        )
                        return False

                    if temp not in modes_used[level].keys():
                        _LOGGER.error(
                            "Invalid %s device JSON file '%s': invalid 'temperature' '%s' command key used.",
                            device_class,
                            file_name,
                            temp,
                        )
                        return False
                    modes_used[level][temp] += 1
            else:
                for mode in commands.keys():
                    if mode not in modes_used[level].keys():
                        _LOGGER.error(
                            "Invalid %s device JSON file '%s': not defined '%s' mode '%s' command key used.",
                            device_class,
                            file_name,
                            level,
                            mode,
                        )
                        return False
                    elif not DeviceData.check_file_climate_commands(
                        file_name,
                        depth + 1,
                        modes_list,
                        modes_used,
                        commands_used,
                        device_class,
                        check_data,
                        commands[mode],
                    ):
                        return False
                    modes_used[level][mode] += 1

        return True

    @staticmethod
    def check_file_fan(file_name, device_data, device_class, check_data):
        if not (
            "speed" in device_data
            and isinstance(device_data["speed"], list)
            and len(device_data["speed"])
        ):
            _LOGGER.error(
                "Invalid %s device JSON file '%s': missing or invalid attribute 'speed'.",
                device_class,
                file_name,
            )
            return False
        return True

    @staticmethod
    def check_file_media_player(file_name, device_data, device_class, check_data):
        return True

    @staticmethod
    def precision_round(number, precision):
        if precision == 0.1:
            return round(float(number), 1)
        if precision == 0.5:
            return round((float(number) * 2) / 2.0, 1)
        elif precision == 1:
            return round(float(number))
        elif precision > 1:
            return round(float(number) / int(precision)) * int(precision)
        else:
            return None
