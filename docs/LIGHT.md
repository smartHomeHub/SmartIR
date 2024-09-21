# SmartIR Light

Find your device's brand code [here](LIGHT_CODES.md) and add the number in the `device_code` field. If your device is not supported, you will need to learn your own IR codes and place them in the Json file in `smartir/custom_codes/light` subfolder. Please refer to [this guide](CODES_SYNTAX.md) to find a way how to do it. Once you have working device file please do not forgot to submit Pull Request so it could be inherited to this project for other users.

## Configuration variables

| Name                         |  Type   | Default  | Description   |
| --- | :---: | :---: | --- |
| `name` | string | optional | The name of the device |
| `unique_id` | string | optional | An ID that uniquely identified this device. If two devices have the same unique ID, Home Assistant will raise an exception. |
| `device_code` | number | required | (Accepts only positive numbers) |
| `controller_data` | string | required | The data required for the controller to function. Look into configuration examples below for valid configuration entries for different controller types. |
|  `delay` | number | optional | Adjusts the delay in seconds between multiple commands. The default is 0.5 |
|  `power_sensor` | string | optional | _entity_id_ for a sensor or that monitors whether your device is actually On or Off. This may be a power monitor sensor, or a helper that monitors power usage with a threshold. (Accepts only on/off states) |

## Example (using broadlink controller)

Add a Broadlink RM device named "Bedroom" via config flow (read the [docs](https://www.homeassistant.io/integrations/broadlink/)).

```yaml
smartir:

light:
  - platform: smartir
    name: Bedroom Ceiling Light
    unique_id: bedroom_ceiling_light
    device_code: 1000
    controller_data: remote.bedroom_remote
    power_sensor: binary_sensor.bedroom_light_power
```

## Light configuration

As well as the generic settings, the light supports two lists:
`brightness` and `color_temperature`.  These should be sorted lists
from lower to higher values of brightness on a scale of 1 to 255, and
color temperature in Kelvin (normally from 2700 to 6500).  Supported
commands are "on", "off", "brighten", "dim", "warmer", "colder" and "night".
If "night" is configured, it is implemented as a special brightness step that
can be selected by setting a brightness of 1 (such lights usually have a
separate small and dim nightlight bulb inside the fixture).


## Available codes for Light devices

[**Light codes**](/docs/LIGHT_CODES.md)
