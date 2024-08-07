<p align="center">
  <a href="#"><img src="assets/smartir_climate.png" width="350" alt="SmartIR Climate"></a>
</p>

For this platform to work, we need a .json file containing all the necessary IR commands.
Find your device's brand code [here](CLIMATE.md#available-codes-for-climate-devices) and add the number in the `device_code` field. If your device is not working, you will need to learn your own codes and place the Json file in `smartir/codes/climate` subfolders. ~~[Keite Trần](https://github.com/keitetran/BroadlinkIRTools) developed [an amazing web-based app](https://keitetran.github.io/BroadlinkIRTools/) for this job.~~
_Please note that the device_code field only accepts positive numbers. The .json extension is not required._

## Configuration variables:
| Name | Type | Default | Description |
| ---- | :--: | :-----: | ----------- |
| `name` | string | optional | The name of the device |
| `unique_id` | string | optional | An ID that uniquely identifies this device. If two devices have the same unique ID, Home Assistant will raise an exception. |
| `device_code` | number | required | (Accepts only positive numbers) |
| `controller_data` | string | required | The data required for the controller to function. Enter the entity_id of the Broadlink remote **(must be an already configured device)**, or the entity id of the Xiaomi IR controller, or the MQTT topic on which to send commands. |
| `delay` | number | optional | Adjusts the delay in seconds between multiple commands. The default is 0.5 |
| `temperature_sensor` | string | optional | *entity_id* for a temperature sensor |
| `humidity_sensor` | string | optional | *entity_id* for a humidity sensor |
| `power_sensor` | string | optional | *entity_id* for a sensor that monitors whether your device is actually `on` or `off`. This may be a power monitor sensor. (Accepts only on/off states) |
| `power_sensor_restore_state` | boolean | optional | If `power_sensor` is set, and the device is likely to turn off and back on while still in the set mode (for instance, a minisplit cycling on and off while in heating or cooling mode), setting this to `true` will cause the climate state to update dynamically, following the state of the `power_sensor`. |

## Example (using broadlink controller):
Add a Broadlink RM device named "Bedroom" via config flow (read the [docs](https://www.home-assistant.io/integrations/broadlink/)).

```yaml
smartir:

climate:
  - platform: smartir
    name: Office AC
    unique_id: office_ac
    device_code: 1000
    controller_data: remote.bedroom_remote
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
    power_sensor_restore_state: true
```

## Example (using LOOKin controller):
```yaml
smartir:

climate:
  - platform: smartir
    name: Office AC
    unique_id: office_ac
    device_code: 4000
    controller_data: 192.168.10.10
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
    power_sensor: binary_sensor.ac_power
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

climate:
  - platform: smartir
    name: Office AC
    unique_id: office_ac
    device_code: 8000
    controller_data: my_espir_send_raw_command
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
    power_sensor: binary_sensor.ac_power
```

## Available codes for climate devices:
The following are the code files created by the amazing people in the community. Before you start creating your own code file, try if one of them works for your device. **Please open an issue if your device is working and not included in the supported models.**
Contributing to your own code files is welcome. However, we do not accept incomplete files as well as files related to MQTT controllers.

#### Toyotomi
| Code                               | Supported Models      | Controller |
| ---------------------------------- | --------------------- | ---------- |
| [1000](../codes/climate/1000.json) | AKIRA GAN/GAG-A128 VL | Broadlink  |
| [1001](../codes/climate/1000.json) | AKIRA GAN/GAG A135FW ML | Broadlink |

#### Panasonic
| Code                               | Supported Models                                                   | Controller |
| ---------------------------------- | ------------------------------------------------------------------ | ---------- |
| [1020](../codes/climate/1020.json) | CS-CE7HKEW<br>CS-CE9HKEW<br>CS-CE12HKEW<br>CS-PC24MKF<br>CS-C24PKF | Broadlink  |
| [1021](../codes/climate/1021.json) | CS-RE9GKE<br>CS-RE12GKE<br> CS-RE9PKR<br>CSCU-Z25TKR               | Broadlink  |
| [1022](../codes/climate/1022.json) | CS-Z25TK<br>CS-XN7SKJ                                              | Broadlink  |
| [1023](../codes/climate/1023.json) | CS-HE9JKE<br>CS-HE12JKE<br>CS-HE9LKE                               | Broadlink  |
| [1024](../codes/climate/1024.json) | CS-MRE7MKE                                                         | Broadlink  |
| [1025](../codes/climate/1025.json) | CS-E18FKR                                                          | Broadlink  |
| [1026](../codes/climate/1026.json) | CS-PC12QKT                                                         | Broadlink  |
| [1027](../codes/climate/1027.json) | CS-SA9CKP                                                          | Broadlink  |
| [1028](../codes/climate/1028.json) | CS-U9RKR<br>CS-U12RKR                                              | Broadlink  |
| [1029](../codes/climate/1029.json) | CS-LJ22~LJ90BA2(YA2)<br>C8024-9921 (Remote)                        | Broadlink  |
| [1030](../codes/climate/1030.json) | CS-E12JKDW <b>(Swing mode)</b>	    							  | Broadlink  |
| [1031](../codes/climate/1031.json) | SRK25ZMP-S<br>SRK35ZMP-S<br>SRK45ZMP-S	    					  | Broadlink  |

#### General Electric
| Code                               | Supported Models                                                                               | Controller |
| ---------------------------------- | ---------------------------------------------------------------------------------------------- | ---------- |
| [1040](../codes/climate/1040.json) | Unknown model                                                                                  | Broadlink  |
| [1041](../codes/climate/1041.json) | AE1PH09IWF<br>AE0PH09IWO<br>AE1PH12IWF<br>AE0PH12IWO<br>AE4PH18IWF<br>AE4PH18IWF<br>AE5PH18IWO | Broadlink  |
| [1042](../codes/climate/1042.json) | ASHA09LCC                                                                                      | Broadlink  |
| [1043](../codes/climate/1043.json) | ASWX09LECA                                                                                     | Broadlink  |
| [1044](../codes/climate/1044.json) | AHD08LXW1                                                                                      | Broadlink  |

#### LG
| Code                               | Supported Models                                                     | Controller |
| ---------------------------------- | -------------------------------------------------------------------- | ---------- |
| [1060](../codes/climate/1060.json) | R09AWN<br>R24AWN<br>E09EK                                            | Broadlink  |
| [1061](../codes/climate/1061.json) | Unknown model                                                        | Broadlink  |
| [1062](../codes/climate/1062.json) | LG InverterV P12RK                                                   | Broadlink  |
| [1063](../codes/climate/1063.json) | LG Inverter P12EP1, P12EU (AKB74955603 Remote)                              | Broadlink  |
| [1064](../codes/climate/1064.json) | Unknown model                                                        | Broadlink  |
| [1065](../codes/climate/1065.json) | LG LA080EC,LAXXXEC (AKB73598011 remote)                              | Broadlink  |
| [1066](../codes/climate/1066.json) | LA090HYV<br>LA120HYV<br>LAN090HYV<br>LAN120HYV<br>(AKB73835312 remote) | Broadlink  |
| [1067](../codes/climate/1067.json) | W12TCM | Broadlink  |
| [1068](../codes/climate/1068.json) | AKB74295303 | Broadlink  |
| [1069](../codes/climate/1069.json) | AKB74295304 | Broadlink  |
| [1070](../codes/climate/1070.json) | PC09SQ NSJ | Broadlink  |
| [4060](../codes/climate/4060.json) | G09LH                                                                | Xiaomi     |
| [7062](../codes/climate/7062.json) | LG InverterV P12RK                                                   | ESPHome     |
| [7065](../codes/climate/7065.json) | LG080EC<br>LG100EC<br>LG150EC<br>LG200EC                             | ESPHome     |

#### Hitachi
| Code                               | Supported Models                                              | Controller |
| ---------------------------------- | ------------------------------------------------------------- | ---------- |
| [1080](../codes/climate/1080.json) | RAC-50HK1                                                     | Broadlink  |
| [1081](../codes/climate/1081.json) | RAC-10EH1<br>RAC-18EH1<br>RAS-10EH1<br>RAS-10EH3<br>RAS-18EH1 | Broadlink  |
| [1082](../codes/climate/1082.json) | RAS-25YHA<br>RAS-35YHA                                        | Broadlink  |
| [1083](../codes/climate/1083.json) | RAS-32CNH2                                                    | Broadlink  |
| [1084](../codes/climate/1084.json) | RAS-DX18HDK<br>RAK-35RPC                                      | Broadlink  |
| [1085](../codes/climate/1085.json) | RPA24B3BL                                                     | Broadlink  |
| [1086](../codes/climate/1086.json) | RAC-36NK1<br>RAC-28NK1                                        | Broadlink  |
| [1087](../codes/climate/1087.json) | RAS-E25YHAB<br>RAS-E35YHAB<br>RAS-E50YHAB                     | Broadlink  |
| [1088](../codes/climate/1088.json) | RAF-25REX<br>RAF-35REX<br>RAF-50REX                           | Broadlink  |
| [1089](../codes/climate/1089.json) | RAK-35RXE                                                     | Broadlink  |
| [1090](../codes/climate/1090.json) | RAK-50RPE                                                     | Broadlink  |

#### Daikin
| Code                               | Supported Models                                                                                                                                               | Controller |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| [1100](../codes/climate/1100.json) | FTXS25CVMB<br>FTXS35CVMB<br>FTXS60BVMB<br>FVXS25BVMB                                                                                                           | Broadlink  |
| [1101](../codes/climate/1101.json) | FTXS20LVMA<br>FTXS25LVMA<br>FTXS35LVMA<br>FTXS46LVMA<br>FTXS50LVMA<br>FTXS60LVMA<br>FTXS71LVMA<br>FTXS85LVMA<br>FTXS95LVMA<br>FTXM35M<br>FVXM35F<br>FVXS50FV1B<br> FTXL35J2V1B<br>FTXM25UVMA<br>FTXM35UVMA<br>FTXD25DVMA<br>FTXS35G2V1B<br>FTXM71UVMA<br>FTM09PV2S | Broadlink  |
| [1102](../codes/climate/1102.json) | FTV20AXV14                                                                                                                                                     | Broadlink  |
| [1103](../codes/climate/1103.json) | Unknown model                                                                                                                                                  | Broadlink  |
| [1104](../codes/climate/1104.json) | TF25DVM                                                                                                                                                        | Broadlink  |
| [1105](../codes/climate/1105.json) | FTX12NMVJU                                                                                                                                                     | Broadlink  |
| [1106](../codes/climate/1106.json) | ATX20KV1B<br>ATX25KV1B<br>ATX35KV1B                                                                                                                            | Broadlink  |
| [1107](../codes/climate/1107.json) | FTX25JAV1NB                                                                                                                                                    | Broadlink  |
| [1108](../codes/climate/1108.json) | FTXG25EV1BS<br>FTXG35EV1BS<br>FTXG35EV1BW                                                                                                                                                    | Broadlink  |
| [1109](../codes/climate/1109.json) | BRC4C158 (Remote)                                                                                                                                              | Broadlink  |
| [1110](../codes/climate/1110.json) | FTC15NV14<br>FTC20NV14<br>FTC25NV14<br>FTC35NV14                                                                                                                                              | Broadlink  |
| [1111](../codes/climate/1111.json) | FTE09NV25                                                                                                                                           | Broadlink  |
| [1112](../codes/climate/1112.json) | ATKC09TV2S<br>FTKQ12TV2S                                                                                                                                           | Broadlink  |
| [1113](../codes/climate/1113.json) | FTXV35AV1B<br>FTXS09RL215  | Broadlink  |
| [1114](../codes/climate/1114.json) | FTXM35UVMZ                                                                                                                                           | Broadlink  |
| [1115](../codes/climate/1115.json) | FTXB-C                                                                                                                                           | Broadlink  |
| [1116](../codes/climate/1116.json) | FCQ100KAVEA                                  | Broadlink  |
| [1117](../codes/climate/1117.json) | DTXF35TVMA                                                                                           | Broadlink  |
| [1118](../codes/climate/1118.json) | ARC452A21<br>FTXS09LVJU<br>FTXS12LVJU<br>FTXS15LVJU<br>FTXS18LVJU<br>FTXS24LVJU<br> | Broadlink  |
| [1119](../codes/climate/1119.json) | FTXS60FVMA                                                                                           | Broadlink  |
| [4100](../codes/climate/4100.json) | FTXS25CVMB<br>FTXS35CVMB<br>FTXS60BVMB<br>FVXS25BVMB                                                 | Xiaomi     |
| [4100](../codes/climate/4100.json) | FTXS25CVMB<br>FTXS35CVMB<br>FTXS60BVMB<br>FVXS25BVMB                                                                                                           | Xiaomi     |

#### Mitsubishi Electric
| Code                               | Supported Models                                                                                     | Controller |
|------------------------------------|------------------------------------------------------------------------------------------------------| ---------- |
| [1120](../codes/climate/1120.json) | MSZ-GL25VGD<br>MSZ-GL35VGD<br>MSZ-GL42VGD<br>MSZ-GL50VG<br>MSZ-GL60VGD<br>MSZ-GL71VGD<br>MSZ-GL80VGD | Broadlink  |
| [1121](../codes/climate/1121.json) | MSZ-GA35VA                                                                                           | Broadlink  |
| [1122](../codes/climate/1122.json) | MSZ-AP50VGKD                                                                                         | Broadlink  |
| [1123](../codes/climate/1123.json) | SRK25ZSX<br>SRC25ZSX                                                                                 | Broadlink  |
| [1124](../codes/climate/1124.json) | MSZ-SF25VE3<br>MSZ-SF35VE3<br>MSZ-SF42VE3<br>MSZ-SF50VE<br>MSZ-AP20VG                                | Broadlink  |
| [1125](../codes/climate/1125.json) | MLZ-KP25VF<br>MLZ-KP35VF<br>MLZ-KP50VF                                                               | Broadlink  |
| [1126](../codes/climate/1126.json) | MSX09-NV II <br> MSH-07RV <br> MSH-12RV                                                              | Broadlink  |
| [1127](../codes/climate/1127.json) | MSZ-HJ25VA                                                                                           | Broadlink  |
| [1128](../codes/climate/1128.json) | MSZ-HJ25VA<br>MSZ-HJ35VA                                                                             | Broadlink  |
| [1129](../codes/climate/1129.json) | MSZ-GE22VA<br>MSZ-EF35VE<br>MSZ-GL\*NA                                                               | Broadlink  |
| [1130](../codes/climate/1130.json) | MS-SGD18VC                                                                                           | Broadlink  |
| [1131](../codes/climate/1131.json) | PAR-FL32MA remote                                                                                    | Broadlink  |
| [1132](../codes/climate/1132.json) | MSC-A12YV                                                                                            | Broadlink  |
| [1133](../codes/climate/1133.json) | MSXY-FN10VE<br>MSXY-FN07VE<br>MSXY-FN13VE<br>MSXY-FN18VE <b>(Swing mode)</b> <br> MSY-GN18VF         | Broadlink  |
| [1134](../codes/climate/1134.json) | MG-GN18VF<br>MS-GN18VF<br>MS-GN13VF                                                                  | Broadlink  |
| [1135](../codes/climate/1135.json) | MSZ-GE60VAD<br>MSZ-GE71VAD<br>MSZ-GE80VAD                                                            | Broadlink  |
| [1136](../codes/climate/1136.json) | MSXY-FP10VG<br>MSXY-FP13VG<br>MSXY-FP18VG                                                            | Broadlink  |
| [1137](../codes/climate/1137.json) | MSZ-HR35VF                                                                                           | Broadlink  |
| [1136](../codes/climate/1138.json) | MSZ-FD25VA-E2 (KM09D/0166901 Remote)                                                                 | Broadlink  |
| [1139](../codes/climate/1139.json) | MLZ-KP series (SG176 Remote)                                                                        | Broadlink  |
| [4129](../codes/climate/4129.json) | DXK18Z1-S                                                                                            | Xiaomi v2  |
| [7124](../codes/climate/7124.json) | MSZ-SF25VE3<br>MSZ-SF35VE3<br>MSZ-SF42VE3<br>MSZ-SF50VE<br>MSZ-AP20VG                                | ESPHome |


#### Actron
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1140](../codes/climate/1140.json) | Unknown model    | Broadlink  |

#### Carrier
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1160](../codes/climate/1160.json) | Unknown model    | Broadlink  |
| [1161](../codes/climate/1161.json) | 40GKX-024RB      | Broadlink  |
| [1162](../codes/climate/1162.json) | 42TVGS024-703    | Broadlink  |
| [1163](../codes/climate/1163.json) | 40MAQ*           | Broadlink  |
| [1164](../codes/climate/1164.json) | 42LUVH025N-1     | Broadlink  |

#### Gree
| Code                               | Supported Models                               | Controller  |
|------------------------------------|------------------------------------------------|-------------|
| [1180](../codes/climate/1180.json) | Unknown model                                  | Broadlink   |
| [1181](../codes/climate/1181.json) | Unknown model/Model: GWH09QB / YAN1F1 (Remote) | Broadlink   |
| [1182](../codes/climate/1182.json) | Y512/Y502 (Remote)                             | Broadlink   |
| [1183](../codes/climate/1183.json) | Smart inverter <b>(Swing mode)</b>             | Broadlink   |
| [1184](../codes/climate/1184.json) | GWH09KF<br>GC-EAF09HR                          | Broadlink   |
| [1185](../codes/climate/1185.json) | KFR-50LW<br>YAP1F2                             | Broadlink   |
| [1186](../codes/climate/1186.json) | GWH18ACD-D3DNA 1M                              | Broadlink   |
| [1187](../codes/climate/1187.json) | Unknown model                                  | Broadlink   |
| [4180](../codes/climate/4180.json) | YB0FB2 (Remote)                                | Xiaomi      |
| [4181](../codes/climate/4181.json) | YB1FA  (Remote)                                | Xiaomi (v2) |

#### Tosot
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1200](../codes/climate/1200.json) | Unknown model    | Broadlink  |

#### Sungold
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1220](../codes/climate/1220.json) | Unknown model    | Broadlink  |

#### Consul
| Code                               | Supported Models         | Controller |
| ---------------------------------- | ------------------------ | ---------- |
| [1240](../codes/climate/1240.json) | Unknown model            | Broadlink  |
| [1241](../codes/climate/1241.json) | CBV12CBBNA<br>CBY12DBBNA | Broadlink  |

#### Toshiba
| Code                               | Supported Models                                                                                                 | Controller |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------- | ---------- |
| [1260](../codes/climate/1260.json) | RAS-13NKV-E / RAS-13NAV-E<br>RAS-13NKV-A / RAS-13NAV-A<br>RAS-16NKV-E / RAS-16NAV-E<br>RAS-16NKV-A / RAS-16NAV-A<br>RAS-M10SKV-E | Broadlink  |
| [1261](../codes/climate/1261.json) | WH-TA05NE<br>WH-TA05LE<br>WH-TA11EJ                                                                                           | Broadlink  |
| [1262](../codes/climate/1262.json) | RAC-PD0812CRRU<br>RAC-PD1013CWRU<br>RAC-PD1213CWRU<br>RAC-PD1414CWRU                                             | Broadlink  |
| [1263](../codes/climate/1263.json) | RAS-B07J2KVSG-E<br>RAS-B10J2KVSG-E<br>RAS-B13J2KVSG-E<br>RAS-B10SKVP-E                                           | Broadlink  |
| [1264](../codes/climate/1264.json) | RAS-13SKVR-A                                                                                                     | Broadlink  |
| [7260](../codes/climate/7260.json) | RAS-18NKV2-E                                                                                                     | ESPHome    |

#### Fujitsu
| Code                               | Supported Models                                                        | Controller  |
| ---------------------------------- | ----------------------------------------------------------------------- | ----------- |
| [1280](../codes/climate/1280.json) | AR-RBE1E (Remote control)                                               | Broadlink   |
| [1281](../codes/climate/1281.json) | AR-RY3 (Remote control)<br>AR-RAE1/AR-RAE1E<br>AR-RAH1U                 | Broadlink   |
| [1282](../codes/climate/1282.json) | AR-JW11 (Remote control)                                                | Broadlink   |
| [1283](../codes/climate/1283.json) | AR-AB5 (Remote control)                                                 | Broadlink   |
| [1284](../codes/climate/1284.json) | AR-REG1U (Remote control)                                               | Broadlink   |
| [1285](../codes/climate/1285.json) | AR-RCE1E (Remote control)                                               | Broadlink   |
| [4285](../codes/climate/4285.json) | AR-RCE1E (Remote control)                                               | Xiaomi (v2) |
| [7285](../codes/climate/7285.json) | AR-RCE1E (Remote control)                                               | ESPHome     |
| [1286](../codes/climate/1286.json) | AR-JE5 (Remote control)                                                 | Broadlink   |
| [1287](../codes/climate/1287.json) | AR-REB1E (Remote control)<br>AR-REM7E<br>AR-REW2E                       | Broadlink   |
| [1288](../codes/climate/1288.json) | AR-REB1E (Remote control)                                               | Broadlink   |
| [1289](../codes/climate/1289.json) | AR-REW1E (Remote control)                                               | Broadlink   |
| [1290](../codes/climate/1290.json) | AR-RFL7J (Remote control)                                               | Broadlink   |
| [1291](../codes/climate/1291.json) | AR-REF1E (Remote control)                                               | Broadlink   |
| [1292](../codes/climate/1292.json) | AR-RY12 (Remote control) - <b>vertical and horizontal swing support</b> | Broadlink   |
| [1293](../codes/climate/1293.json) | AR-REB1E (Remote control) - <b>vertical swing support</b>               | Broadlink   |

#### Sharp
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1300](../codes/climate/1300.json) | AY-B22DM         | Broadlink  |
| [1301](../codes/climate/1301.json) | AY-X##BE         | Broadlink  |
| [7300](../codes/climate/7300.json) | AH-AP9GMY        | ESPHome    |

#### Haier
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1320](../codes/climate/1320.json) | Unknown model    | Broadlink  |
| [1321](../codes/climate/1321.json) | Top-Tech 14      | Broadlink  |
| [1322](../codes/climate/1322.json) | HSU-09HPL03/R03  | Broadlink  |

#### Tadiran
| Code                               | Supported Models                       | Controller |
| ---------------------------------- | -------------------------------------- | ---------- |
| [1340](../codes/climate/1340.json) | Unknown model                          | Broadlink  |
| [1341](../codes/climate/1341.json) | TAC490                                 | Broadlink  |
| [1342](../codes/climate/1342.json) | 10i/15i/inv220a                        | Broadlink  |
| [1343](../codes/climate/1343.json) | Alpha Series                           | Broadlink  |
| [1344](../codes/climate/1344.json) | YB1FA Remote (Control) (Swing support) | Broadlink  |
| [1345](../codes/climate/1345.json) | TAC-297 Remote (Control)               | Broadlink  |

#### Springer
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [1360](../codes/climate/1360.json) | Split Hi Wall Maxiflex | Broadlink  |

#### Midea
| Code                               | Supported Models               | Controller |
| ---------------------------------- | ------------------------------ | ---------- |
| [1380](../codes/climate/1380.json) | Unknown model                  | Broadlink  |
| [1381](../codes/climate/1381.json) | Unknown model                  | Broadlink  |
| [1382](../codes/climate/1382.json) | MSY-12HRDN1 (Works also for Kastron AC / Remote RG57A2/BGEF)  | Broadlink  |
| [1383](../codes/climate/1383.json) | KFR-35G                        | Broadlink  |
| [1384](../codes/climate/1384.json) | MSMACU-18HRFN1-QRD0GW          | Broadlink  |
| [1385](../codes/climate/1385.json) | R11HG/E                        | Broadlink  |
| [1386](../codes/climate/1386.json) | KFR-32GW                       | Broadlink  |
| [1387](../codes/climate/1387.json) | RG70E/BGEF (Remote)            | Broadlink  |
| [1388](../codes/climate/1388.json) | 42MAQA09S5                     | Broadlink  |
| [1389](../codes/climate/1389.json) | MAP05R1WWT                     | Broadlink  |
| [1390](../codes/climate/1390.json) | RG52C1/BGE (Remote)            | Broadlink  |
| [1391](../codes/climate/1391.json) | RG58E3/BGEF (Remote)           | Broadlink  |
| [1392](../codes/climate/1392.json) | MPD-12CRN7                     | Broadlink  |
| [1393](../codes/climate/1393.json) | Polario MPPHB-09CRN7-Q         | Broadlink  |
| [4380](../codes/climate/4380.json) | MCD-24HRN1-Q1<br>RAS-10N3KVR-E | Xiaomi     |
| [4381](../codes/climate/4381.json) | RG70C1/BGEF | Xiaomi     |
| [7386](../codes/climate/7386.json) | KFR-32GW                       | ESPHome    |

#### Samsung
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1400](../codes/climate/1400.json) | Unknown model    | Broadlink  |
| [1401](../codes/climate/1401.json) | AR##HSF/JFS##    | Broadlink  |
| [1402](../codes/climate/1402.json) | AR##TSHGAWK      | Broadlink  |
| [1403](../codes/climate/1403.json) | AR##TXHZ##       | Broadlink  |
| [1404](../codes/climate/1404.json) | AR##TSHZ##       | Broadlink  |
| [1405](../codes/climate/1405.json) | AR##TSHQBURN     | Broadlink  |
| [1406](../codes/climate/1406.json) | AQV12PWD         | Xiaomi     |

#### Sintech
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1420](../codes/climate/1420.json) | KFR-34GW         | Broadlink  |

#### Akai
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1440](../codes/climate/1440.json) | Unknown model    | Broadlink  |
| [1441](../codes/climate/1441.json) | TEM-26CHSAAK5<br>TEM-70CHSAAK5<br>TEM-26CHSAKA5<br>TEM-35CHSAKA<br>TEM-50CHSAKA<br>TEM-35CHSABH<br>TEM-35CHSF    | Broadlink  |

#### Alliance
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1460](../codes/climate/1460.json) | Unknown model    | Broadlink  |

#### Junkers
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1480](../codes/climate/1480.json) | Excellence       | Broadlink  |
| [1481](../codes/climate/1481.json) | Excellence (Auto Swing)  | Broadlink  |

#### Sanyo
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1500](../codes/climate/1500.json) | Unknown          | Broadlink  |
| [1501](../codes/climate/1501.json) | SAP-KR124EHEA    | Broadlink  |

#### Hisense
| Code                               | Supported Models   | Controller |
| ---------------------------------- | ------------------ | ---------- |
| [1520](../codes/climate/1520.json) | Unknown            | Broadlink  |
| [1521](../codes/climate/1521.json) | Unknown            | Broadlink  |
| [1522](../codes/climate/1522.json) | DG11R2-01 (Remote) (Also works for Zephyr ZE-18CA17) | Broadlink  |
| [5520](../codes/climate/5520.json) | AS-07UR4SYDD815G   | LOOKin  |

#### Whirlpool
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1540](../codes/climate/1540.json) | SPIS412L         | Broadlink  |

#### Tadiran
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1560](../codes/climate/1560.json) | WIND 3P          | Broadlink  |

#### Chigo
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1580](../codes/climate/1580.json) | ZH/JT-03 (Remote)| Broadlink  |
| [1581](../codes/climate/1581.json) | ZH/JT-03 (Remote)| Broadlink  |
| [1582](../codes/climate/1582.json) | ZH/TT-14 (Remote)| Broadlink  |
| [4580](../codes/climate/4580.json) | Unknown          | Xiaomi (v2)|

#### Beko
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1600](../codes/climate/1600.json) | BEVCA 120        | Broadlink  |
| [1601](../codes/climate/1601.json) | BPAK 120         | Broadlink  |
| [1602](../codes/climate/1602.json) | BXK 120          | Broadlink  |
| [1603](../codes/climate/1603.json) | BXEU 090         | Broadlink  |

#### Tornado
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1620](../codes/climate/1620.json) | Unknown          | Broadlink  |
| [1621](../codes/climate/1621.json) | Super Legend 40  | Broadlink  |
| [1622](../codes/climate/1622.json) | Master-22 X      | Broadlink  |
| [1623](../codes/climate/1623.json) | Inverter VRF     | Broadlink  |
| [1624](../codes/climate/1624.json) | Saga by tornado  | Broadlink  |
| [1625](../codes/climate/1625.json) | Inverter VRF BOX | Broadlink  |
| [1626](../codes/climate/1626.json) | Master-35 X      | Broadlink  |

#### Fujiko
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1640](../codes/climate/1640.json) | Unknown          | Broadlink  |

#### Royal
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1660](../codes/climate/1660.json) | 08HPN1T1         | Broadlink  |
| [1661](../codes/climate/1661.json) | RC-G25HN         | Broadlink  |

#### Mitsubishi Heavy
| Code                               | Supported Models                                     | Controller |
| ---------------------------------- | ---------------------------------------------------- | ---------- |
| [1680](../codes/climate/1680.json) | SRK25ZJ-S1<br>SRK13CRV-S1                            | Broadlink  |
| [1681](../codes/climate/1681.json) | SRK71ZK-S                                            | Broadlink  |
| [1682](../codes/climate/1681.json) | SRKM25H<br>SRK40HBE<br>RKS502A502<br>RKS502A503      | Broadlink  |
| [1683](../codes/climate/1683.json) | DXK12ZMA-S                                           | Broadlink  |
| [1684](../codes/climate/1684.json) | DXK24ZRA                                             | Broadlink  |
| [1685](../codes/climate/1685.json) | SRK50ZS-S<br>DXKZ6W18                                | Broadlink  |
| [1686](../codes/climate/1686.json) | SRK20ZSA-W<br>SRK25ZSA-W<br>SRK35ZSA-W<br>SRK50ZSA-W | Broadlink  |
| [1687](../codes/climate/1687.json) | SRK35ZJX-S<br>SRK20ZJX-S                             | Broadlink  |
| [1688](../codes/climate/1688.json) | SRK25ZSP-W<br>SRK35ZSP-W<br>SRK45ZSP-W               | Broadlink  |
| [1689](../codes/climate/1689.json) | DXK12ZSA-W                                           | Broadlink  |
| [1690](../codes/climate/1690.json) | FDUM VF2                                             | Broadlink  |
| [1691](../codes/climate/1691.json) | SRK71ZRA-W                                           | Broadlink  |
| [1692](../codes/climate/1692.json) | DXK12Z3-S<br>DXK09Z5-S<br>DXK15Z5-S                  | Broadlink  |

#### Electrolux
| Code                               | Supported Models                                                                                                                                                                             | Controller |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| [1700](../codes/climate/1700.json) | EACS/I-HAT/N3                                                                                                                                                                                | Broadlink  |
| [1701](../codes/climate/1701.json) | EACS-HA                                                                                                                                                                                      | Broadlink  |
| [1702](../codes/climate/1702.json) | QI/QE09F<br>QI/QE09R<br>QI/QE12F<br>QI/QE12R<br>QI/QE18F<br>QI/QE18R<br>QI/QE22F<br>QI/QE22R<br>XI/XE09F<br>XI/XE09R<br>XI/XE12F<br>XI/XE12R<br>XI/XE18F<br>XI/XE18R<br>XI/XE22F<br>XI/XE22R | Broadlink  |
| [1703](../codes/climate/1703.json) | EXP26U758CW   | Broadlink  |
| [1704](../codes/climate/1704.json) | EPI12LEIWI   | Broadlink  |

#### Erisson
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1720](../codes/climate/1720.json) | EC-S07T2         | Broadlink  |

#### Kelvinator
| Code                               | Supported Models              | Controller |
| ---------------------------------- | ----------------------------- | ---------- |
| [1740](../codes/climate/1740.json) | KSV25HRG (RG57A6/BGEF Remote) | Broadlink  |
| [1741](../codes/climate/1741.json) | KSV26CRC<br/>KSV26HRC<br/>KSV35CRC<br/>KSV35HRC<br/>KSV53HRC<br/>KSV62HRC<br/>KSV70CRC<br/>KCV70HRC<br/>KSV80HRC | Broadlink  |
| [7740](../codes/climate/7740.json) | KSV25HWH                      | ESPHome    |

#### Daitsu
| Code                               | Supported Models                      | Controller |
| ---------------------------------- | ------------------------------------- | ---------- |
| [1760](../codes/climate/1760.json) | DS12U-RV (or any using R51M/E remote) | Broadlink  |
| [1761](../codes/climate/1761.json) | DS-9KIDT                              | Broadlink  |
| [1762](../codes/climate/1762.json) | ASD9KI-DT                             | Broadlink  |
| [1763](../codes/climate/1763.json) | DOS12KIDB                             | Broadlink  |
| [1764](../codes/climate/1764.json) | DS-12KIDC(WD)                         | Broadlink  |

#### Trotec
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1780](../codes/climate/1780.json) | YX1F6 (Remote)   | Broadlink  |
| [1781](../codes/climate/1781.json) | YX1F (Remote)   | Broadlink  |
| [1782](../codes/climate/1782.json) | RG57H3(B)/BGCEF-M<br>PAC 2100 X<br>PAC 2600 X  | Broadlink  |

#### BALLU
| Code                               | Supported Models    | Controller |
| ---------------------------------- | ------------------- | ---------- |
| [1800](../codes/climate/1800.json) | YKR-K/002E (Remote) | Broadlink  |
| [1801](../codes/climate/1801.json) | BSD/in-09HN1_20Y | Broadlink  |

#### Riello
| Code                               | Supported Models  | Controller |
| ---------------------------------- | ----------------- | ---------- |
| [1820](../codes/climate/1820.json) | WSI XN<br>RAR-3U4 | Broadlink  |

#### Hualing
| Code                               | Supported Models            | Controller |
| ---------------------------------- | --------------------------- | ---------- |
| [1840](../codes/climate/1840.json) | KFR-45GW/JNV<br>KFR-45G/JNV | Broadlink  |

#### Simbio
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1860](../codes/climate/1860.json) | Unknown          | Broadlink  |

#### Saunier Duval
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1880](../codes/climate/1880.json) | Unknown          | Broadlink  |

#### TCL
| Code                               | Supported Models  | Controller |
|------------------------------------|-------------------| ---------- |
| [1900](../codes/climate/1900.json) | TAC-12CHSD/XA21I  | Broadlink  |
| [1901](../codes/climate/1901.json) | TAC-12CHSD/XA71IN | Broadlink  |

#### Aokesi
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1920](../codes/climate/1920.json) | Unknown          | Broadlink  |

#### Electra
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1940](../codes/climate/1940.json) | Unknown          | Broadlink  |
| [1941](../codes/climate/1941.json) | iGo              | Broadlink  |
| [1942](../codes/climate/1942.json) | Electra Classic  | Broadlink  |
| [1943](../codes/climate/1943.json) | Electra Classic14| Broadlink  |
| [1944](../codes/climate/1944.json) | Electra Platinum Plus Inverter| Broadlink  |
| [1945](../codes/climate/1945.json) | Unknown model (Swing support) | Broadlink  |
| [1946](../codes/climate/1946.json) | RC-3 | Broadlink  |

#### AUX
| Code                               | Supported Models     | Controller |
| ---------------------------------- | -------------------- | ---------- |
| [1960](../codes/climate/1960.json) | Unknown              | Broadlink  |
| [1961](../codes/climate/1961.json) | AUX FREEDOM AUX-09FH | Broadlink  |
| [1962](../codes/climate/1962.json) | iClima ICI-09A (YKR-H/101E remote) (Also works with Mundo Clima MUPR-12-H9A) | Broadlink  |

#### Fuji
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [1980](../codes/climate/1980.json) | Unknown          | Broadlink  |

#### Aeronik
| Code                               | Supported Models     | Controller |
| ---------------------------------- | -------------------- | ---------- |
| [2000](../codes/climate/2000.json) | ASO-12IL<br>ASI-12IL | Broadlink  |

#### Ariston
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2020](../codes/climate/2020.json) | A-IFWHxx-IGX     | Broadlink  |

#### Pioneer
| Code                               | Supported Models                 | Controller |
| ---------------------------------- | -------------------------------- | ---------- |
| [2040](../codes/climate/2040.json) | WYS018GMFI17RL<br>WYS009GMFI17RL<br>CB018GMFILCFHD<br>CB012GMFILCFHD | Broadlink  |
| [2041](../codes/climate/2041.json) | WT018GLFI19HLD | Broadlink  |
#### Dimplex
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2060](../codes/climate/2060.json) | GDPAC12RC        | Broadlink  |

#### Sendo
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2080](../codes/climate/2080.json) | SND-18IK         | Broadlink  |

#### Mirage
| Code                               | Supported Models   | Controller |
| ---------------------------------- | ------------------ | ---------- |
| [2100](../codes/climate/2100.json) | Magnum Inverter 19 | Broadlink  |

#### Technibel
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2120](../codes/climate/2120.json) | MPAF13A0R5IAA    | Broadlink  |

#### Unionaire
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2140](../codes/climate/2140.json) | Artify           | Broadlink  |

#### Lennox
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2160](../codes/climate/2160.json) | Unknown          | Broadlink  |
| [2161](../codes/climate/2161.json) | LNMTE026V2       | Broadlink  |
| [2162](../codes/climate/2162.json) | LNINVE052<br>LNINVC052       | Broadlink  |

#### Hokkaido
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [2180](../codes/climate/2180.json) | LA09-DUAL H1     | Broadlink  |

#### IGC
| Code                               | Supported Models   | Controller |
| ---------------------------------- | ------------------ | ---------- |
| [2200](../codes/climate/2200.json) | RAK-12NH<br>RAK-18NH | Broadlink  |

#### Blueridge
| Code                               |      Supported Models      | Controller |
| ---------------------------------- | -------------------------- | ---------- |
| [2220](../codes/climate/2220.json) | RG57A4<br>RG57A6<br>BGEFU1 | Broadlink  |

#### Delonghi
| Code                               | Supported Models        | Controller |
|------------------------------------|-------------------------| ---------- |
| [2240](../codes/climate/2240.json) | PAC N82ECO<br>PAC AN111 | Broadlink  |
| [2241](../codes/climate/2241.json) | PAC EM77                | Broadlink  |
| [2242](../codes/climate/2242.json) | PAC AN140HPEW           | Broadlink  |

#### Profio
| Code                               | Supported Models        | Controller |
| ---------------------------------- | ----------------------- | ---------- |
| [2260](../codes/climate/2260.json) | Unknown                 | Broadlink  |

#### Hantech
| Code                               | Supported Models        | Controller |
| ---------------------------------- | ----------------------- | ---------- |
| [2280](../codes/climate/2280.json) | A018-12KR2              | Broadlink  |
| [2281](../codes/climate/2281.json) | A016-09KR2/A            | Broadlink  |

#### Zanussi
| Code                               | Supported Models        | Controller |
| ---------------------------------- | ----------------------- | ---------- |
| [2300](../codes/climate/2300.json) | ZH/TT-02 (Remote)       | Broadlink  |
| [2301](../codes/climate/2301.json) | ZACS/I-07 HPF/A17/N1    | Broadlink  |

#### Whynter
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2320](../codes/climate/2320.json) | ARC-08WB<br>ARC-10WB<br>ARC-126MD<br>ARC-126MDB<br>ARC-148MS | Broadlink  |
| [2321](../codes/climate/2321.json) | ARC-12S<br>ARC-12SD<br>ARC-122DS<br>ARC-14S<br>ARC-141BG<br>ARC-143MX<br>ARC-101CW | Broadlink  |

#### Vortex
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2340](../codes/climate/2340.json) | VOR-12C3/407           | Broadlink  |

#### Flouu
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2360](../codes/climate/2360.json) | Unknown                | Broadlink  |

#### Baxi
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2380](../codes/climate/2380.json) | Unknown (It also works with Vortex VAI-A1221FFWR (YKR-H/009E remote))               | Broadlink  |

#### Yamatsu
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2400](../codes/climate/2400.json) | YAM-12KDA<br>AUS-07C53R013L24| Broadlink  |

#### VS
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2420](../codes/climate/2420.json) | YKR-F06                | Broadlink  |

#### Vaillant
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2440](../codes/climate/2440.json) | ClimaVair VAI 8-025    | Broadlink  |

#### FanWorld
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2460](../codes/climate/2460.json) | FanWorld FW6-3000      | Broadlink  |

#### Rotenso
| Code                               | Supported Models                  | Controller |
| ---------------------------------- | --------------------------------- | ---------- |
| [2480](../codes/climate/2480.json) | Ukura<br>Maze (Remote control)    | Broadlink  |

#### Endesa
| Code                               | Supported Models                  | Controller |
| ---------------------------------- | --------------------------------- | ---------- |
| [2500](../codes/climate/2500.json) | DGR11    | Broadlink  |

#### Galanz
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2520](../codes/climate/2520.json) | GZ-1002B-E3 (Remote)   | Broadlink  |

#### Audinac
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2540](../codes/climate/2540.json) | SP3500			      | Broadlink  |

#### Mistral
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2560](../codes/climate/2560.json) | MPAC15CY28		      | Broadlink  |

#### Korel
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2580](../codes/climate/2580.json) | KSAL2-09DCEH		      | Broadlink  |

#### Equation
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2600](../codes/climate/2600.json) | RCH-143   		      | Broadlink  |

#### Komeco
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2620](../codes/climate/2620.json) | Unknown                | Broadlink  |

#### Fisher
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2640](../codes/climate/2640.json) | FPR-91DE4-R<br>FPR-121DE4-R<br>FPR-141DE4-R | Broadlink  |
| [2641](../codes/climate/2641.json) | FSOAI-SU-90AE2 | Broadlink  |

#### Hyundai
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2660](../codes/climate/2660.json) | HSE09PH5V              | Broadlink  |
| [2661](../codes/climate/2661.json) | HY6INV                 | Broadlink  |
| [2662](../codes/climate/2662.json) | H-ARI22-09H            | Broadlink  |

#### Apton
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2680](../codes/climate/2680.json) | AFC-100T               | Broadlink  |

#### Kolin
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2700](../codes/climate/2700.json) | RC-M7B1 (Remote) <b>(Swing mode)</b>| Broadlink  |
| [8700](../codes/climate/8700.json) | KAG-145RSINV           | ESPHome    |

#### AEG
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2720](../codes/climate/2720.json) | AXP35U538CW            | Broadlink  |

#### Bosch
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2740](../codes/climate/2740.json) | 5000i		          | Broadlink  |

#### Tristar
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2760](../codes/climate/2760.json) | AC-5400                | Broadlink  |

#### Xiaomi
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2780](../codes/climate/2780.json) | KFR-35G/F3C1           | Broadlink  |

#### Elgin
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2800](../codes/climate/2800.json) | HVQI18B2IA             | Broadlink  |
| [2801](../codes/climate/2801.json) | HVQI12B2FB             | Broadlink  |

#### Pearl
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2820](../codes/climate/2820.json) | EXGC24FCBC1            | Broadlink  |

#### HTW
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2840](../codes/climate/2840.json) | HTWS035IX21D2-R32-I    | Broadlink  |

#### Senville
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2860](../codes/climate/2860.json) | SENA/12HF/IZ           | Broadlink  |

#### Bora
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2880](../codes/climate/2880.json) | 18SRA-HE           | Broadlink  |

#### Goodman
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2900](../codes/climate/2900.json) | MSH123E21AXAA<br>MST183E20ACAA | Broadlink  |

#### Best
| Code                               | Supported Models       | Controller |
| ---------------------------------- | ---------------------- | ---------- |
| [2920](../codes/climate/2920.json) | BSTS18CNE2 | Broadlink  |

#### SAGA
| Code                               | Supported Models | Controller |
|------------------------------------|------------------| ---------- |
| [2940](../codes/climate/2940.json) | SAGA-A-22(CH)    | Broadlink  |

#### EcoAir
| Code                               | Supported Models | Controller |
|------------------------------------|------------------| ---------- |
| [2960](../codes/climate/2960.json) | Unknown          | Broadlink  |

#### Agratto
| Code                               | Supported Models            | Controller |
|------------------------------------|-----------------------------|------------|
| [2980](../codes/climate/2980.json) | ECST12FR4-02 ECST19QFIR4-02 | Broadlink  |

#### Philco
| Code                               | Supported Models            | Controller |
|------------------------------------|-----------------------------|------------|
| [3000](../codes/climate/3000.json) | PAC9000ITQFM9W | Broadlink  |

#### Klasse
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3020](../codes/climate/3020.json) | DOZ-S06JT        | Broadlink  |

#### Viessmann
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3040](../codes/climate/3040.json) | Vitoclima 300-S  | Broadlink  |

#### HappyTree
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3060](../codes/climate/3060.json) | TAC-12CHSD/XA81  | Broadlink  |

### Voltas
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3080](../codes/climate/3080.json) | INV/AC 1.5T 183V MZJ3 3S  | Broadlink  |

#### Cecotec
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3100](../codes/climate/3100.json) | EnergySilence 12000 AirClima (05290)  | Broadlink  |

### TechnoLux
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [4800](../codes/climate/4800.json) | KFR-25GW/F  | Xiaomi  |

### Cooper & Hunter
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3120](../codes/climate/3120.json) | Unknown  | Broadlink  |

### Argo
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3140](../codes/climate/3140.json) | Ulisse13  | Broadlink  |

### Aqua Thermal
| Code                               | Supported Models | Controller |
|------------------------------------|------------------|------------|
| [3160](../codes/climate/3160.json) | LM AURI-12  | Broadlink  |

#### Devanti
| Code                               | Supported Models | Controller |
| ---------------------------------- | ---------------- | ---------- |
| [3180](../codes/climate/3180.json) | WAC-05C-WH       | Broadlink  |

#### Friedrich
| Code                               | Supported Models | Controller |
| ---------------------------------- | -----------------| ---------- |
| [3200](../codes/climate/3200.json) | CP12G10B         | Broadlink  |

#### Mundoclima
| Code                               | Supported Models | Controller |
| ---------------------------------- | -----------------| ---------- |
| [3220](../codes/climate/3220.json) | MUPR-09-H9A<br>MUPR-12-H9A<br>MUPR-18-H9A<br>MUPR-24-H9A<br>MUPR-09-H5A<br>MUPR-12-H5A<br>MUPR-18-H5A<br>MUPR-24-H5A      | Broadlink  |

#### Casper
| Code                               | Supported Models | Controller |
| ---------------------------------- | -----------------| ---------- |
| [3240](../codes/climate/3240.json) | SC-09FS32        | Broadlink  |

#### Family
| Code                               | Supported Models | Controller |
| ---------------------------------- | -----------------| ---------- |
| [3260](../codes/climate/3260.json) | 12WIFI           | Broadlink  |

#### Sigma
| Code                               | Supported Models | Controller |
| ---------------------------------- | -----------------| ---------- |
| [3280](../codes/climate/3280.json) | SGS32H13NE       | Broadlink  |
