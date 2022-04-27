<p align="center">
  <a href="#"><img src="assets/smartir_mediaplayer.png" width="350" alt="SmartIR Media Player"></a>
</p>

For this platform to work, we need a .json file containing all the necessary IR commands.
Find your device's brand code [here](MEDIA_PLAYER.md#available-codes-for-tv-devices) and add the number in the `device_code` field. The compoenent will download it to the correct folder. If your device is not working, you will need to learn your own codes and place the .json file in `smartir/codes/media_player/` subfolders. Please note that the `device_code` field only accepts positive numbers. The .json extension is not required.

## Configuration variables:
**name** (Optional): The name of the device<br />
**unique_id** (Optional): An ID that uniquely identifies this device. If two devices have the same unique ID, Home Assistant will raise an exception.<br />
**device_code** (Required): ...... (Accepts only positive numbers)<br />
**controller_data** (Required): The data required for the controller to function. Enter the IP address of the Broadlink device **(must be an already configured device)**, or the entity id of the Xiaomi IR controller, or the MQTT topic on which to send commands.<br />
**delay** (Optional): Adjusts the delay in seconds between multiple commands. The default is 0.5 <br />
**power_sensor** (Optional): *entity_id* for a sensor that monitors whether your device is actually On or Off. This may be a power monitor sensor. (Accepts only on/off states)<br />
**source_names** (Optional): Override the names of sources as displayed in HomeAssistant (see below)<br />

## Example (using broadlink controller):
Add a Broadlink RM device named "Bedroom" via config flow (read the [docs](https://www.home-assistant.io/integrations/broadlink/)).

```yaml
smartir:

media_player:
  - platform: smartir
    name: Living room TV
    unique_id: living_room_tv
    device_code: 1000
    controller_data: remote.bedroom_remote
    power_sensor: binary_sensor.tv_power
```

## Example (using xiaomi controller):
```yaml
smartir:

remote:
  - platform: xiaomi_miio
    host: 192.168.10.10
    token: YOUR_TOKEN
    
media_player:
  - platform: smartir
    name: Living room TV
    unique_id: living_room_tv
    device_code: 2000
    controller_data: remote.xiaomi_miio_192_168_10_10
    power_sensor: binary_sensor.tv_power
```

## Example (using mqtt controller):
```yaml
smartir:

media_player:
  - platform: smartir
    name: Living room TV
    unique_id: living_room_tv
    device_code: 3000
    controller_data: home-assistant/living-room-tv/command
    power_sensor: binary_sensor.tv_power
```

## Example (using LOOKin controller):
```yaml
smartir:

media_player:
  - platform: smartir
    name: Living room TV
    unique_id: living_room_tv
    device_code: 4000
    controller_data: 192.168.10.10
    power_sensor: binary_sensor.tv_power
```

## Example (using ESPHome):
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
            code: !lambda 'return command;'

remote_transmitter:
  pin: GPIO14
  carrier_duty_percent: 50%
```
HA configuration.yaml:
```yaml
smartir:

media_player:
  - platform: smartir
    name: Living room TV
    unique_id: living_room_tv
    device_code: 2000
    controller_data: my_espir_send_raw_command
    power_sensor: binary_sensor.tv_power
```

### Overriding Source Names
Source names in device files are usually set to the name that the media player uses. These often aren't very descriptive, so you can override these names in the configuration file. You can also remove a source by setting its name to `null`.

```yaml
media_player:
  - platform: smartir
    name: Living room TV
    unique_id: living_room_tv
    device_code: 1000
    controller_data: 192.168.10.10
    source_names:
      HDMI1: DVD Player
      HDMI2: Xbox
      VGA: null
```

### Changing channels
Most IR remotes can only send one key at a time (0 to 9) to change your TV channel, changing to other channels requires pressing 2 consecutive keys. SmartIR handles any channel for you with the standard Home Assistant service interface. Here is an example that changes your Kitchen TV to channel 51:

```yaml
service: media_player.play_media
target:
  entity_id: media_player.kitchen_tv
data:
  media_content_id: 51
  media_content_type: "channel"
```

## Available codes for TV devices:
The following are the code files created by the amazing people in the community. Before you start creating your own code file, try if one of them works for your device. **Please open an issue if your device is working and not included in the supported models.**
Contributing to your own code files is welcome. However, we do not accept incomplete files as well as files related to MQTT controllers.

#### Philips
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1000](../codes/media_player/1000.json)|26PFL560H|Broadlink

#### Sony
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1020](../codes/media_player/1020.json)|KDL-46HX800|Broadlink

#### LG
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1040](../codes/media_player/1040.json)|22MT47DC|Broadlink
[1041](../codes/media_player/1041.json)|LH6235D|Broadlink
[1042](../codes/media_player/1042.json)|43UM7510PSB<br>OLED55B8SSC<br>OLED55B9PLA|Broadlink
[1043](../codes/media_player/1043.json)|32LC2R|Broadlink

#### Samsung
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1060](../codes/media_player/1060.json)|UE40F6500<br>LE40D550<br>UE40H6400<br>UE40H7000SL|Broadlink
[1061](../codes/media_player/1061.json)|UE40C6000<br>UE40D6500<br>UE32H5500<br>UE22D5000|Broadlink
[1062](../codes/media_player/1062.json)|UE40C6000<br>UE40D6500<br>UE32H5500<br>UE22D5000<br>UN46D6000SF|Broadlink
[1063](../codes/media_player/1063.json)|UN55JU7500|Broadlink
[7060](../codes/media_player/7060.json)|UA32EH5000M|ESPHome

#### Insignia
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1080](../codes/media_player/1080.json)|NS-42D510NA15|Broadlink

#### Toshiba
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1100](../codes/media_player/1100.json)|42C3530D|Broadlink

#### Yamaha
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1120](../codes/media_player/1120.json)|Unknown|Broadlink
[1121](../codes/media_player/1121.json)|Yamaha RX-V375 and others (RAV463/ZA113500 remote)|Broadlink
[1122](../codes/media_player/1122.json)|VR50590 remote|Broadlink
[1123](../codes/media_player/1123.json)|AS201|Broadlink

#### RME
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1140](../codes/media_player/1140.json)|ADI-2 DAC FS|Broadlink

#### Logitech
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1160](../codes/media_player/1160.json)|Z906|Broadlink
[1161](../codes/media_player/1161.json)|Z-5500|Broadlink
[1162](../codes/media_player/1162.json)|Z-5450|Broadlink

#### TCL
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1180](../codes/media_player/1180.json)|55EP640|Broadlink
[1181](../codes/media_player/1181.json)|43S6500FS|Broadlink

#### Pace
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1200](../codes/media_player/1200.json)|TDS850NNZ <br> TDC850NF|Broadlink

#### Silver
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1220](../codes/media_player/1220.json)|MEO|Broadlink

#### TurboX
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1240](../codes/media_player/1240.json)|TXV-2420|Broadlink

#### Thomson
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1260](../codes/media_player/1260.json)|40FA3203|Broadlink

#### Grunding
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1280](../codes/media_player/1280.json)|GSB-810|Broadlink

#### OKI
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1300](../codes/media_player/1300.json)|V19B-LED4|Broadlink

#### Sky
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1320](../codes/media_player/1320.json)|SkyQ Black<br>SkyQ Mini|Broadlink

#### Bauhn
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1340](../codes/media_player/1340.json)|Aldi|Broadlink

#### Optoma
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1360](../codes/media_player/1360.json)| HD27 |Broadlink

#### Xiaomi
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1380](../codes/media_player/1380.json)| MiBox<br>MItv |Broadlink

#### Pioneer
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1400](../codes/media_player/1400.json)| X-CM56 |Broadlink

#### JBL
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1420](../codes/media_player/1420.json)| Cinema SB160 |Broadlink

#### Andersson
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1440](../codes/media_player/1440.json)| L4223FDC PVR |Broadlink

#### ZTE
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[7460](../codes/media_player/7460.json)| B860H | ESPHome