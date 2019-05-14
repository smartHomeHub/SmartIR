<p align="center">
  <a href="#"><img src="assets/smartir_climate.png" width="350" alt="SmartIR Climate"></a>
</p>

For this platform to work, we need a .json file containing all the necessary IR commands.

* If you previously used the Broadlink IR Climate component you should use [this tool](../tools) to convert your old INI files. If you have uploaded your old INI files on GitHub, I have already converted them. Find your device's brand code [here](https://github.com/smartHomeHub/blob/master/Docs/CLIMATE.md#available-codes-for-climate-devices) and add the number in the `device_code` field. The compoenent will download it to the correct folder.
* For new users, find your device's brand code [here](CLIMATE.md#available-codes-for-climate-devices) and add the number in the `device_code` field. If your device is not working, you will need to learn your own codes and place the Json file in `smartir/codes/climate` subfolders. [Keite Trần](https://github.com/keitetran/BroadlinkIRTools) developed [an amazing web-based app](https://keitetran.github.io/BroadlinkIRTools/) for this job.
_Please note that the device_code field only accepts positive numbers. The .json extension is not required._

## Configuration variables:
**name** (Optional): The name of the device<br />
**unique_id** (Optional): An ID that uniquely identifies this device. If two devices have the same unique ID, Home Assistant will raise an exception.<br />
**device_code** (Required): .... (Accepts only positive numbers)<br />
**controller_data** (Required): The data required for the controller to function. Enter the IP address of the Broadlink device **(must be an already configured device)**, or the entity id of the Xiaomi IR controller, or the MQTT topic on which to send commands.<br />
**temperature_sensor** (Optional): *entity_id* for a temperature sensor<br />
**humidity_sensor** (Optional): *entity_id* for a humidity sensor<br />
**power_sensor** (Optional): *entity_id* for a sensor that monitors whether your device is actually On or Off. This may be a power monitor sensor. (Accepts only on/off states)<br />

## Example (using broadlink controller):
```yaml
smartir:

switch:
  - platform: broadlink
    host: 192.168.10.10
    mac: '00:00:00:00:00:00'
    
climate:
  - platform: smartir
    name: Office AC
    unique_id: office_ac
    device_code: 1000
    controller_data: 192.168.10.10
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
    power_sensor: binary_sensor.ac_power
```

## Example (using xiaomi controller):
```yaml
smartir:

remote:
  - platform: xiaomi_miio
    host: 192.168.10.10
    token: YOUR_TOKEN
    
climate:
  - platform: smartir
    name: Office AC
    unique_id: office_ac
    device_code: 2000
    controller_data: remote.xiaomi_miio_192_168_10_10
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
    power_sensor: binary_sensor.ac_power
```

## Example (using mqtt controller):
```yaml
smartir:
    
climate:
  - platform: smartir
    name: Office AC
    unique_id: office_ac
    device_code: 3000
    controller_data: home-assistant/office-ac/command
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
    power_sensor: binary_sensor.ac_power
```

## Available codes for climate devices:
Below are the code files created by the people in the community. Before you start creating your own code file, try if one of them works for your device. **Please open an issue if your device is working and not included in the supported models.**

#### Toyotomi
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1000](../codes/climate/1000.json)|AKIRA GAN/GAG-A128 VL|Broadlink

#### Panasonic
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1020](../codes/climate/1020.json)|CS-CE7HKEW<br>CS-CE9HKEW<br>CS-CE12HKEW|Broadlink
[1021](../codes/climate/1021.json)|CS-RE9GKE<br>CS-RE12GKE|Broadlink
[1022](../codes/climate/1022.json)|CS-Z25TK|Broadlink
[1023](../codes/climate/1023.json)|CS-HE9JKE<br>CS-HE12JKE|Broadlink

#### General Electric
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1040](../codes/climate/1040.json)|Unknown model|Broadlink

#### LG
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1060](../codes/climate/1060.json)|R09AWN<br>R24AWN<br>E09EK|Broadlink
[1061](../codes/climate/1061.json)|Unknown model|Broadlink
[1062](../codes/climate/1062.json)|LG InverterV P12RK|Broadlink
[1063](../codes/climate/1063.json)|LG Inverter P12EP1 (AKB74955603 Remote)|Broadlink

#### Hitachi
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1080](../codes/climate/1080.json)|Unknown model|Broadlink
[1081](../codes/climate/1081.json)|RAS-10EH3|Broadlink

#### Daikin
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1100](../codes/climate/1100.json)|Unknown model|Broadlink
[1101](../codes/climate/1101.json)|FTXS20LVMA<br>FTXS25LVMA<br>FTXS35LVMA<br>FTXS46LVMA<br>FTXS50LVMA<br>FTXS60LVMA<br>FTXS71LVMA<br>FTXS85LVMA<br>FTXS95LVMA|Broadlink

#### Mitsubishi Electric
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1120](../codes/climate/1120.json)|MSZ-GL25VGD<br>MSZ-GL35VGD<br>MSZ-GL42VGD<br>MSZ-GL50VG<br>MSZ-GL60VGD<br>MSZ-GL71VGD<br>MSZ-GL80VGD|Broadlink
[1121](../codes/climate/1121.json)|MSZ-GA35VA|Broadlink

#### Actron
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1140](../codes/climate/1140.json)|Unknown model|Broadlink

#### Carrier
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1160](../codes/climate/1160.json)|Unknown model|Broadlink

#### Gree
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1180](../codes/climate/1180.json)|Unknown model|Broadlink
[1181](../codes/climate/1181.json)|Unknown model|Broadlink

#### Tosot
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1200](../codes/climate/1200.json)|Unknown model|Broadlink

#### Sungold
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1220](../codes/climate/1220.json)|Unknown model|Broadlink

#### Consul
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1240](../codes/climate/1240.json)|Unknown model|Broadlink

#### Toshiba
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1260](../codes/climate/1260.json)|RAS-13NKV-E / RAS-13NAV-E<br>RAS-13NKV-A / RAS-13NAV-A<br>RAS-16NKV-E / RAS-16NAV-E<br>RAS-16NKV-A / RAS-16NAV-A|Broadlink

#### Fujitsu
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1280](../codes/climate/1280.json)|AR-RBE1E (Remote control)|Broadlink
[1281](../codes/climate/1281.json)|AR-RAE1/AR-RAE1E|Broadlink
[1282](../codes/climate/1282.json)|AR-JW11 (Remote control)|Broadlink
[1283](../codes/climate/1283.json)|AR-AB5 (Remote control)|Broadlink
[1284](../codes/climate/1284.json)|AR-REG1U (Remote control)|Broadlink

#### Sharp
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1300](../codes/climate/1300.json)|AY-B22DM|Broadlink

#### Haier
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1320](../codes/climate/1320.json)|Unknown model|Broadlink

#### Tadiran
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1340](../codes/climate/1340.json)|Unknown model|Broadlink

#### Springer
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1360](../codes/climate/1360.json)|Split Hi Wall Maxiflex|Broadlink

#### Midea
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1380](../codes/climate/1380.json)|Unknown model|Broadlink
[1381](../codes/climate/1381.json)|Unknown model|Broadlink
[3380](../codes/climate/3380.json)|MCD-24HRN1-Q1|Xiaomi

#### Samsung
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1400](../codes/climate/1400.json)|Unknown model|Broadlink
[1401](../codes/climate/1401.json)|AR##HSF/JFS##|Broadlink

#### Sintech
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1420](../codes/climate/1420.json)|KFR-34GW|Broadlink

#### Akai
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1440](../codes/climate/1440.json)|Unknown model|Broadlink

#### Alliance
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1460](../codes/climate/1460.json)|Unknown model|Broadlink

#### Junkers
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1480](../codes/climate/1480.json)|Excellence|Broadlink

#### Sanyo
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1500](../codes/climate/1500.json)|Unknown|Broadlink

#### Hisense
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1520](../codes/climate/1520.json)|Unknown|Broadlink
[1521](../codes/climate/1521.json)|Unknown|Broadlink

#### Whirlpool
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1540](../codes/climate/1540.json)|SPIS412L|Broadlink

#### Tadiran
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1560](../codes/climate/1560.json)|WIND 3P|Broadlink

#### Chigo
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1580](../codes/climate/1580.json)|Unknown|Broadlink

#### Beko
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1600](../codes/climate/1600.json)|BEVCA 120|Broadlink

#### Tornado
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1620](../codes/climate/1620.json)|Unknown|Broadlink

#### Fujiko
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1640](../codes/climate/1640.json)|Unknown|Broadlink

#### Royal
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1660](../codes/climate/1660.json)|08HPN1T1|Broadlink

#### Mitsubishi Heavy
| Code | Supported Models | Controller |
| ------------- | -------------------------- | ------------- |
[1680](../codes/climate/1680.json)|SRK25ZJ-S1|Broadlink
[1681](../codes/climate/1681.json)|SRK71ZK-S|Broadlink
