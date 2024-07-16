# ⏻ Smart IR

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![License](https://img.shields.io/github/license/litinoveweedle/smartir?style=for-the-badge)](https://raw.githubusercontent.com/litinoveweedle/smartir/master/LICENSE)
[![Latest Release](https://img.shields.io/github/v/release/litinoveweedle/smartir?style=for-the-badge)](https://github.com/litinoveweedle/smartir/releases)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge)](https://github.com/psf/black)

## Overview
SmartIR is a custom integration for controlling **climate devices**, **media players** and **fans** via infrared controllers.

SmartIR currently supports the following controllers:
* [Broadlink](https://www.home-assistant.io/integrations/broadlink/)
* [Xiaomi IR Remote (ChuangmiIr)](https://www.home-assistant.io/integrations/remote.xiaomi_miio/)
* [LOOK.in Remote](http://look-in.club/devices/remote)
* [ESPHome User-defined service for remote transmitter](https://esphome.io/components/api.html#user-defined-services)
* [MQTT Publish service](https://www.home-assistant.io/docs/mqtt/service/)
  * [Tuya Z06/Moes UFO-R11 zigbee2mqtt](https://www.zigbee2mqtt.io/devices/UFO-R11.html) 
* [ZHA Zigbee IR remote](https://www.home-assistant.io/integrations/zha/) (May require custom zha quirk for given controller)

More than 120 climate devices are currently supported out-of-the-box, mainly for the Broadlink controller, thanks to our awesome community.

Don't forget to **star** the repository if you had fun!

## Disclaimer ##

This is a fork of the original repository smartHomeHub/SmartIR which seems to be unmaintained at the time with many pull requests pending. As some of those were useful to my usage I decided to fork and merge the work of the corresponding authors to allow for simple usage of the integration through HACS. Therefore all the corresponding rights belong to the original authors. I also lately started to fix some additional users issues, implementing HomeAssistant future compatibility changes and adding some functionality, trying to keep compatibility but please note, that there may be some **breaking changes** from the original version.

### WARNING - custom codes! ###

If you use any own/custom codes json files please backup such json files before migrating to this integration from the original one. After instalation (using HACS) please place your custom files into new `custom_codes` directory. `codes` directory is managed by HACS and you will loose all changes during any HACS update!S

## Documentation ##

[Read the documents for detailed instructions on how to configure SmartIR.](https://github.com/litinoveweedle/SmartIR/)
