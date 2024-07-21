# SmartIR Devices Codes Files syntax

## Disclaimer

- I do not provide any support for you to record your own device codes. Please do not create any issues to ask how to do it as it will immediately closed.
- [You can ask for help at SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/).
- If you think something is missing or wrong in the docs and you would like to submit PR with docs amendments you are welcome.

## Device code JSON file

If you decide to modify or create your own device file you need to do it in the `custom_code/[climate|fan|media_player|/` directory. Any changes inside `codes` directory will be lost upon SmartIR HACS update!

- If you need to modify existing file from the `code` directory please copy it into `custom_codes` first.
- If you need to create new device file please choose free for digit file name (not used by existing json file int the `codes/your_class` directory) and create json file with given name in the `custom_codes/your_class`

Each different class (Climate, Fan, Media Player) device file has common part and then class specific part. Please take look to some existing files as examples. It is very easy to make error in JSON file structure when editing. Use any available JSON format checker to validate it after editing - for example [JSON Lint](https://jsonlint.com/)

## Common declaration part

```yaml:
{
    "manufacturer": "Toyotomi",
    "supportedModels": [
        "AKIRA GAN/GAG-A128 VL"
    ],
    "supportedController": "Broadlink",
    "commandsEncoding": "Base64",
```

| json attribute        | mandatory |        type        | description                                                                                                                                                   |
| --------------------- | :-------: | :----------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `manufacturer`        |   `yes`   |      `string`      | Manufacturer name of the device you intend to control                                                                                                         |
| `supportedModels`     |   `yes`   | `array of strings` | List of devices names supported by this file                                                                                                                  |
| `supportedController` |   `yes`   |      `string`      | Controller type used. Can be one of the `Broadlink`, `Xiaomi`, `MQTT`, `LOOKin`, `ESPHome`, `ZHA`, `UFOR11`                                                   |
| `commandsEncoding`    |   `yes`   |      `string`      | Each controller type supports given type/s of the IR command encodings. For actual supported encodings for your controller refer to the `controller_const.py` |

## Climate specific

### Climate declaration part

```yaml:
    "temperatureUnit": "C",
    "minTemperature": 16,
    "maxTemperature": 30,
    "precision": 1,
    "operationModes": [
        "auto"
        "heat",
        "cool",
        "heat_cool",
        "fan_only",
        "dry"
    ],
    "presetModes": [
        "none",
        "eco",
        "hi_power"
    ],
    "fanModes": [
        "low",
        "mid",
        "high",
        "auto"
    ],
    "swingModes": [
        "off",
        "",
        "high",
        "auto"
    ],
```

| json attribute    | mandatory |        type        | description                                                                                                                                                                                                                                                                                                                |
| ----------------- | :-------: | :----------------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `temperatureUnit` |   `yes`   |      `string`      | Temperature unit used by you device (this can be different to the HA default temperature unit). Can be one of rhe `C`, `F`, `K`                                                                                                                                                                                            |
| `minTemperature`  |   `yes`   |    `int, float`    | Minimum device supported temperature. Can be float or integer depending on the `precision`                                                                                                                                                                                                                                 |
| `maxTemperature`  |   `yes`   |    `int, float`    | Maximum device supported temperature. Can be float or integer depending on the `precision`                                                                                                                                                                                                                                 |
| `precision`       |   `yes`   |    `int, float`    | This is size of the temperature steps you can set in the target temperature (if you set you temperature in 1 degree steps it will be `1`, if in half degrees it will be `0.5`, etc). Supported precisions are `2`, `1`, `0.5`, `0.1`                                                                                       |
| `operationModes`  |   `yes`   | `array of strings` | List of the modes your device can operate in. This has to be subset of the HA climate [HVAC modes](https://developers.home-assistant.io/docs/core/entity/climate#hvac-modes). No customs modes are possible! Do not list `off` mode here it is included by default.                                                        |
| `presetModes`     |   `no`    | `array of strings` | List of the preset modes your device can operate in. Does you device support dirent ways to operate under any given operationMode? For example can your AC units can do `eco` and `hi-power` cooling? Than those shall be listed here. The preset modes names could be freely defined to match naming used by your device. |
| `fanModes`        |   `no`    | `array of strings` | List of the fan modes your device can operate in. Does you device support fan modes? High, low, auto, etc.? Than those shall be listed here. The fan modes names could be freely defined to match naming used by your device.                                                                                              |
| `swingModes`      |   `no`    | `array of strings` | List of the fan swing modes your device can operate in. Does you device support different ways how your fan grills move? Than those shall be listed here. The swing modes names could be freely defined to match naming used by your device.                                                                               |

### Climate commands

Now when all modes supported by your device (operation, presets, fan, swing) are declared, you need to records IR command for their combination for any target temperature. There may be some tools to help you to help with such process.

The structure shall look like:

`operation mode` -> `preset mode` -> `fan mode` -> `swing mode` -> `temperature` -> `recorded IR command`

```yaml:
    "commands": {
        "cool": {
            "eco": {
                "low": {
                    "swing": {
                        "16": "JgCSAAABKZIXEBcRFz.............",
                        "17": "JgCSAAABKHQKDGgDHz.............",
                        ...
                    },
```

- If your device doesn't support some of the modes types at all (and you did not declare them in the declaration part - for example presetModes are not supported) then simply skip given level (`operation mode` -> `fan mode` -> `swing mode` -> `temperature` -> `recorded IR command`).

```yaml:
    "commands": {
        "cool": {
            "low": {
                "swing": {
                    "16": "JgCSAAABKZIXEBcRFz.............",
                    "17": "JgCSAAABKHQKDGgDHz.............",
                    ...
                },
```

- If you device doesn't support some mode under given higher level mode (for example temperatures are not supported under fan_only operation mode, or presetModes are not supported under dry operation mode), you have three possibilities how to address this:

  1. Use `-` as 'catch all' mode name/temperature. Using this approach has additional behavior - if you change mode/temperature which to the value covered by `-` the value will not change in the HA. (example temperatures are not supported under fan_only operation mode - when you will try to change temperature using `-` key the temperature in HA stays same):

  ```yaml:
  "commands": {
      "fan_only": {
          "-": {
              "low": {
                  "swing": {
                      "-": "JgCSAAABKZIXEBcRFz............."
                  },
  ```

  2. Define some default mode (i.e. something like `none` or `default` but any name will do) as first in the declaration section and use it as default failover mode. (if you are running for example in the operation mode `cool` with preset mode `eco` and you change operation mode to `dry` which doesn't support presets, then it will try to select first available preset in the order presets are declared in the `presetModes` - and it will therefore choose your first one - `none`):

  ```yaml:
  "commands": {
      "dry": {
          "none": {
              "low": {
                  "swing": {
                      "-": "JgCSAAABKZIXEBcRFz............."
                  },
  ```

  3. Duplicate same IR command to all keys for example where all the temperature changes in the fan_only :

  ```yaml:
  "commands": {
      "fan_only": {
          "-": {
              "low": {
                  "swing": {
                      "16": "JgCSAAABKZIXEBcRFz.............",
                      "17": "JgCSAAABKZIXEBcRFz.............",
                      "18": "JgCSAAABKZIXEBcRFz.............",
                      ...
                  },
  ```

## Fan Speficic

TBD

## Media Player specific

TBD
