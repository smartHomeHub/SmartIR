<p align="center">
  <a href="#"><img src="http://www.tooltip.gr/github_assets/smartir_mediaplayer.png" width="350" alt="SmartIR Media Player"></a>
</p>

## Installation:
Create a new folder into the Home Assistant's `custom_components` folder and name it `smartir`. Copy `__init__.py` and `media_player.py` into the `smartir` folder. Create the subfolders `codes/media_player` into the `smartir` folder and copy the code file for your device.

## Configuration variables:
**name** (Optional): Name to use in the frontend<br />
**device_code** (Required): ...... (Accepts only positive numbers)<br />
**controller_send_service** (Required): The service that will be used to send the commands. Only `broadlink_send_packet` (Broadlink controller) is currently supported.<br />
**power_sensor** (Optional): *entity_id* for a sensor that monitors whether your device is actually On or Off. This may be a power monitor sensor. (Accepts only on/off states)<br />

## Example (using broadlink controller):
```yaml
switch:
  - platform: broadlink
    host: 192.168.10.10
    mac: '00:00:00:00:00:00'
    
media_player:
  - platform: smartir
    name: Living room TV
    device_code: 1000
    controller_send_service: switch.broadlink_send_packet_192_168_10_10
    power_sensor: binary_sensor.tv_power
```

## Create your own codes:
ToDo... I'm developing a windows tool to easily create your code files. Please be patient!
