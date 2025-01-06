<p align="center">
    <a href="#"><img src="assets/smartir_light.png" width="350" alt="SmartIR light"></a>
</p>

For this platform to work, we need a .json file containing all the necessary IR or RF commands.
Find your device's brand code [here](LIGHT.md#available-codes-for-light-devices) and add the number in the `device_code` field. The component will download it to the correct folder.  If your device is not working, you will need to learn your own codes and place the .json file in `smartir/codes/fan` subfolders. Please note that the `device_code` field only accepts positive numbers. The .json extension is not required.

## Configuration variables

**name** (Optional): The name of the device<br />
**nuique_id** (Optional): An ID that uniquely identified this device. If two devices have the same unique ID, Home Assistant will raise an exception.<br />
**device_code** (Required): ...... (Accepts only positive numbers)<br />
**controller_data** (Required): The data required for the controller to function. Enter the entity_id of the Broadlink or Xiaomi IR controller, or the MQTT topic on which to send commands.<br />
**delay** (Optional): Adjusts the delay in seconds between multiple commands. The default is 0.5 <br />
**power_sensor** (Optional): *entity_id* for a sensor that monitors whether your device is actually On or Off. This may be a power monitor sensor. (Accepts only on/off states)<br />

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

The following are the code files created by the amazing people in the community. Before you start creating your own code file, try if one of them works for your device. **Please open an issue if your device is working and not included in the supported models.**
Contributing your own code files is welcome. However, we do not accept incomplete files as well as files related to MQTT controllers.

#### Iris Ohyama

| Code                             | Supported Models | Controller |
|----------------------------------|------------------|------------|
| [1000](../codes/light/1000.json) | LEDHCL-R2        | Broadlink  |

#### NEC

| Code                             | Supported Models | Controller |
|----------------------------------|------------------|------------|
| [1020](../codes/light/1020.json) | RE0201 CH1       | Broadlink  |
| [1021](../codes/light/1021.json) | RE0201 CH2       | Broadlink  |

#### Toshiba

| Code                             | Supported Models | Controller |
|----------------------------------|------------------|------------|
| [1040](../codes/light/1040.json) | FRC-199T         | Broadlink  |

#### Takizumi

| Code                             | Supported Models | Controller |
|----------------------------------|------------------|------------|
| [1060](../codes/light/1060.json) | TLR-002          | Broadlink  |
