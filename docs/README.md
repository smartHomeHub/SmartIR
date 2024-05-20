[![](https://img.shields.io/github/v/release/litinoveweedle/SmartIR.svg?style=flat-square)](https://github.com/litinoveweedle/SmartIR/releases/latest) [![](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/custom-components/hacs)

## Overview
SmartIR is a custom integration for controlling **climate devices**, **media players** and **fans** via infrared controllers.<br>
SmartIR currently supports the following controllers:
* [Broadlink](https://www.home-assistant.io/integrations/broadlink/)
* [Xiaomi IR Remote (ChuangmiIr)](https://www.home-assistant.io/integrations/remote.xiaomi_miio/)
* [LOOK.in Remote](http://look-in.club/devices/remote)
* [ESPHome User-defined service for remote transmitter](https://esphome.io/components/api.html#user-defined-services)
* [MQTT Publish service](https://www.home-assistant.io/docs/mqtt/service/)

More than 120 climate devices are currently supported out-of-the-box, mainly for the Broadlink controller, thanks to our awesome community.<br><br>
Don't forget to **star** the repository if you had fun!<br><br>

## Disclaimer ##

This is a fork of the original repository smartHomeHub/SmartIR which seems to be unmaintained at the time with many pull requests pending. As some of those were useful to my usage I decided to fork and merge the work of the corresponding authors to allow for simple usage of the integration through HACS. Therefore all the corresponding rights belong to the original authors. I also lately started to fix some additional users issues, implementing HomeAssistant future compatibility changes and adding some functionality, trying to keep compatibility but please note, that there may be some **breaking changes** from the original version.

## Installation
### *Manual*
Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder).
It should look similar to this:
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
```

### *HACS*
If you want HACS to handle installation and updates, add SmartIR as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/). In this case, it is recommended that you turn off automatic updates, as above.
<br><br>


## Platform setup instructions
Click on the links below for instructions on how to configure each platform.
* [Climate platform](/docs/CLIMATE.md)
* [Media Player platform](/docs/MEDIA_PLAYER.md)
* [Fan platform](/docs/FAN.md)
<br><br>

## See also
* [Discussion about SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/)
* [SmartIR Chat on Telegram](https://t.me/smartHomeHub)

