# SmartIR Fan

For this platform to work, we need a .json file containing all the necessary IR or RF commands.
Find your device's brand code [here](FAN.md#available-codes-for-fan-devices) and add the number in the `device_code` field. If your device is not working, you will need to learn your own codes and place the .json file in `smartir/custom_codes/fan/` subfolders. Please note that the `device_code` field only accepts positive numbers. The .json extension is not required.

## Configuration variables

| Name                         |  Type   | Default  | Description                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------- | :-----: | :------: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`                       | string  | optional | The name of the device                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `unique_id`                  | string  | optional | An ID that uniquely identifies this device. If two devices have the same unique ID, Home Assistant will raise an exception.                                                                                                                                                                                                                                                                                                               |
| `device_code`                | number  | required | (Accepts only positive numbers)                                                                                                                                                                                                                                                                                                                                                                                                           |
| `controller_data`            | string  | required | The data required for the controller to function. Enter the entity_id of the Broadlink remote **(must be an already configured device)**, or the entity id of the Xiaomi IR controller, or the MQTT topic on which to send commands, or the ZHA zigbee cluster to send commands to.                                                                                                                                                       |
| `delay`                      | number  | optional | Adjusts the delay in seconds between multiple commands. The default is 0.5                                                                                                                                                                                                                                                                                                                                                                |
| `power_sensor`               | string  | optional | _entity_id_ for a sensor that monitors whether your device is actually `on` or `off`. This may be a power monitor sensor. (Accepts only on/off states)                                                                                                                                                                                                                                                                                    |
| `power_sensor_delay`         |   int   | optional | Maximum delay in second in which power sensor is able to report back to HA changed state of the device, default is 10 seconds. If sensor reaction time is longer extend this time, otherwise you might get unwanted changes in the device state.                                                                                                                                                                                          |
| `power_sensor_restore_state` | boolean | optional | If `true` than in case power sensor will report to HA that device is `on` without HA actually switching it `on `(device was switched on by remote, of device cycled, etc.), than HA will report last assumed state and attributes at the time when the device was `on` managed by HA. If set to `false` when device will be reported as `on` by the power sensors all device attributes will be reported as `UNKNOWN`. Default is `true`. |

## Example configurations

### Example (using broadlink controller)

Add a Broadlink RM device named "Bedroom" via config flow (read the [docs](https://www.home-assistant.io/integrations/broadlink/)).

```yaml
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 1000
    controller_data: remote.bedroom_remote
    power_sensor: binary_sensor.fan_power
```

## Example (using xiaomi controller)

```yaml
remote:
  - platform: xiaomi_miio
    host: 192.168.10.10
    token: YOUR_TOKEN

fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 2000
    controller_data: remote.xiaomi_miio_192_168_10_10
    power_sensor: binary_sensor.fan_power
```

### Example (using mqtt/Z06/UFO-R11 controller)

```yaml
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 3000
    controller_data: home-assistant/bedroom-fan/command
    power_sensor: binary_sensor.fan_power
```

### Example (using LOOKin controller)

```yaml
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 4000
    controller_data: 192.168.10.10
    power_sensor: binary_sensor.fan_power
```

### Example (using ESPHome)

ESPHome configuration example:

```yaml
esphome:
  name: my_espir
  platform: ESP8266
  board: esp01_1m

api:
  services:
    - service: send_raw_command
      variables:
        command: int[]
      then:
        - remote_transmitter.transmit_raw:
            code: !lambda "return command;"

remote_transmitter:
  pin: GPIO14
  carrier_duty_percent: 50%
```

HA configuration.yaml:

```yaml
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 4000
    controller_data: my_espir_send_raw_command
    power_sensor: binary_sensor.fan_power
```

### Example (using ZHA controller and a TuYa ZS06)

```yaml
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 5000
    controller_data: '{
     "ieee":"XX:XX:XX:XX:XX:XX:XX:XX",
     "endpoint_id": 1,
     "cluster_id": 57348,
     "cluster_type": "in",
     "command": 2,
     "command_type": "server"
    }'
    power_sensor: binary_sensor.fan_power
```

## Available codes for Fan devices

The following are the code files created by the amazing people in the community. Before you start creating your own code file, try if one of them works for your device. **Please clone this repo and open Pull Request to include your own working and not included codes in the supported models.** Contributing to your own code files is most welcome.

[**Fan codes**](/docs/FAN_CODES.md)
