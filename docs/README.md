# ⏻ Smart IR

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/litinoveweedle/smartir?style=for-the-badge)](https://github.com/litinoveweedle/smartir/blob/main/LICENSE)
[![Latest Release](https://img.shields.io/github/v/release/litinoveweedle/smartir?style=for-the-badge)](https://github.com/litinoveweedle/smartir/releases)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

## Overview

SmartIR is a custom integration for controlling **climate devices**, **media players** and **fans** via infrared controllers.

SmartIR currently supports the following controllers:

- [Broadlink](https://www.home-assistant.io/integrations/broadlink/)
- [Xiaomi IR Remote (ChuangmiIr)](https://www.home-assistant.io/integrations/remote.xiaomi_miio/)
- [LOOK.in Remote](http://look-in.club/devices/remote)
- [ESPHome User-defined service for remote transmitter](https://esphome.io/components/api.html#user-defined-services)
- [MQTT Publish service](https://www.home-assistant.io/docs/mqtt/service/)
  - [Tuya Z06/Moes UFO-R11 zigbee2mqtt](https://www.zigbee2mqtt.io/devices/UFO-R11.html)
- [ZHA Zigbee IR remote](https://www.home-assistant.io/integrations/zha/) (May require custom zha quirk for given controller)

More than 120 climate devices are currently supported out-of-the-box, mainly for the Broadlink controller, thanks to our awesome community.

Don't forget to **star** the repository if you had fun!

## Disclaimer

This is a fork of the original repository smartHomeHub/SmartIR which seems to be unmaintained at the time with many pull requests pending. As some of those were useful to my usage I decided to fork and merge the work of the corresponding authors to allow for simple usage of the integration through HACS. Therefore all the corresponding rights belong to the original authors. I also lately started to fix some additional users issues, implementing HomeAssistant future compatibility changes and adding some functionality, trying to keep compatibility but please note, that there may be some **breaking changes** from the original version.

### WARNING - custom codes!

If you use any own/custom codes json files please backup such json files before migrating to this integration from the original one. After instalation (using HACS) please place your custom files into new `custom_codes` directory. `codes` directory is managed by HACS and you will loose all changes during any HACS update!

## Installation

### _HACS_

If you want HACS to handle installation and updates, add SmartIR url `https://github.com/litinoveweedle/SmartIR` as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) in the HACS. This is preffered instalation method as it would allow for automatic updates.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=litinoveweedle&repository=SmartIR&category=Integration)

### _Manual_

Download latest smartir.zip file and place it's content in the `custom_components` folder in your HomeAssistant configuration `custom_component/smartir` directory.
The resulting directory structure should look similar to this:

```
<config directory>/
|-- custom_components/
|   |-- smartir/
|       |-- __init__.py
|       |-- climate.py
        |-- controller.py
|       |-- fan.py
|       |-- media_player.py
|       |-- codes/
|           |-- climate/
|               |-- 1000.json
|               |-- .....
|           |-- fan/
|               |-- 1000.json
|               |-- .....
|           |-- media_player/
|               |-- 1000.json
|               |-- .....
|       |-- custom_codes/
|           |-- climate/
|               |-- 1000.json
|               |-- .....
|           |-- fan/
|               |-- 1000.json
|               |-- .....
|           |-- media_player/
|               |-- 1000.json
|               |-- .....
```

## Device Data - IR Codes

To properly function, specification of your controlled device data including IR codes shall exists either in `codes` or in `custom_codes` directory as a .JSON file. When installed both using HACS or manual method, `codes` directory is populated by device data files maintained by this project. If you would like to create your own device data file, place it in the `custom_codes` class `climate|fan|media_player` subdirectory, this directory is persistent and will be manitained accross HACS updates. **Please don't forget to create [PR](https://github.com/litinoveweedle/SmartIR/pulls) for this new device data file and I will try to include it in a new releases.**

### Convert IR Codes from Broadlink to Z06/UFO-R11

Using https://gist.github.com/svyatogor/7839d00303998a9fa37eb48494dd680f?permalink_comment_id=5153002#gistcomment-5153002 you can convert Broadlink code file.

Example: `python3 broadlink_to_tuya.py 1287.json > 9997.json`

## Platform setup instructions

Click on the links below for instructions on how to configure each platform.

- [Climate platform](/docs/CLIMATE.md)
- [Media Player platform](/docs/MEDIA_PLAYER.md)
- [Fan platform](/docs/FAN.md)

## See also

- [Discussion about SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/)
