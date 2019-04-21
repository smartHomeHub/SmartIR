<p align="center">
  <a href="#"><img src="assets/smartir_fan.png" width="350" alt="SmartIR Media Player"></a>
</p>

For this platform to work, we need a .json file containing all the necessary IR or RF commands.
Find your device's brand code [here](FAN.md#available-codes-for-fan-devices) and add the number in the `device_code` field. The compoenent will download it to the correct folder. If your device is not working, you will need to learn your own codes and place the .json file in `smartir/codes/fan/` subfolders. Please note that the `device_code` field only accepts positive numbers. The .json extension is not required.

## Configuration variables:
**name** (Optional): The name of the device<br />
**unique_id** (Optional): An ID that uniquely identifies this device. If two devices have the same unique ID, Home Assistant will raise an exception.<br />
**device_code** (Required): ...... (Accepts only positive numbers)<br />
**controller_send_service** (Required): The service that will be used to send the commands. Only `broadlink_send_packet` (Broadlink controller) and `mqtt.publish` is currently supported.<br />
**controller_command_topic** (Optional): MQTT topic on which to send commands when *controller_send_service* is mqtt.publish<br />
**power_sensor** (Optional): *entity_id* for a sensor that monitors whether your device is actually On or Off. This may be a power monitor sensor. (Accepts only on/off states)<br />

## Example (using broadlink controller):
```yaml
smartir:

switch:
  - platform: broadlink
    host: 192.168.10.10
    mac: '00:00:00:00:00:00'
    
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 1000
    controller_send_service: switch.broadlink_send_packet_192_168_10_10
    power_sensor: binary_sensor.fan_power
```
Make sure the broadlink switch is already installed. Go to the Home Assistant UI/dev service, find the broadlink send_packet service and copy the name of it.
Add the name of the send_packet service to the `controller_send_service` field.

## Example (using mqtt controller):
```yaml
smartir:
    
fan:
  - platform: smartir
    name: Bedroom fan
    unique_id: bedroom_fan
    device_code: 2000
    controller_send_service: mqtt.publish
    controller_command_topic: home-assistant/bedroom-fan/command
    power_sensor: binary_sensor.fan_power
```

## Available codes for Fan devices:
Below are the code files created by the people in the community. Before you start creating your own code file, try if one of them works for your device. **Please open an issue if your device is working and not included in the supported models.**

#### Kaze
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1000](../codes/fan/1000.json)|Unknown|Broadlink

#### Acorn
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1020](../codes/fan/1020.json)|Unknown|Broadlink

#### Lucci Air
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1040](../codes/fan/1040.json)|Aria|Broadlink

#### Super Fan
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1060](../codes/fan/1060.json)|A1|Broadlink
