[![](https://img.shields.io/github/v/release/smartHomeHub/SmartIR.svg?style=flat-square)](https://github.com/smartHomeHub/SmartIR/releases/latest) [![](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/custom-components/hacs)

## Overview
SmartIR is a custom integration for controlling **climate devices**, **media palyers** and **fans** via infrared controllers.<br>
SmartIR currently supports the following controllers:
* [Broadlink](https://www.home-assistant.io/integrations/broadlink/)
* [Xiaomi IR Remote (ChuangmiIr)](https://www.home-assistant.io/integrations/remote.xiaomi_miio/)
* [LOOK.in Remote](http://look-in.club/devices/remote)
* [ESPHome User-defined service for remote transmitter](https://esphome.io/components/api.html#user-defined-services)
* [MQTT Publish service](https://www.home-assistant.io/docs/mqtt/service/)

More than 120 climate devices are currently supported out-of-the-box, mainly for the Broadlink controller, thanks to our awesome community.<br>
Please don't forget to **star** the repository if you had fun! [**"Buy Me A Coffee**"](https://www.buymeacoffee.com/vassilis) is also welcome. It will help in further development.<br><br>


## Installation
### *Manual*
**(1)** Place the `custom_components` folder in your configuration directory (or add its contents to an existing `custom_components` folder).
It should look similar to this:
```
<config directory>/
|-- custom_components/
|   |-- smartir/
|       |-- __init__.py
|       |-- climate.py
|       |-- fan.py
|       |-- media_player.py
|       |-- etc...
```
**(2)** Add the following to your configuration.yaml file.
```yaml
smartir:
```

<br>
SmartIR automatically detects updates after each HA startup and asks you to install them. It also has a mechanism that prevents you from updating if the last SmartIR version is incompatible with your HA instance. You can disable this feature by setting SmartIR as follows:

```yaml
smartir:
  check_updates: false
```

If you would like to get updates from the rc branch (Release Candidate), configure SmartIR as follows:
```yaml
smartir:
  update_branch: rc
```

### *HACS*
If you want HACS to handle the updates, add SmartIR as a custom repository. In this case, it is recommended that you turn off automatic updates, as above.
<br><br>

## Platform setup instructions
Click on the images below for instructions on how to configure each platform.
<p align="center">
  <a href="CLIMATE.md"><img src="assets/smartir_climate.png" width="250" alt="SmartIR Climate" style="margin-right: 30px"></a>
  <a href="MEDIA_PLAYER.md"><img src="assets/smartir_mediaplayer.png" width="250" alt="SmartIR Media Player" style="margin-right: 30px"></a>
  <a href="FAN.md"><img src="assets/smartir_fan.png" width="250" alt="SmartIR Media Player" style="margin-right: 30px"></a>
</p>
<br>

## Links
* [SmartIR Chat on Telegram](https://t.me/smartHomeHub)
* [Discussion about SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/)

<br><br>
<p align="center">
  <a href="https://www.buymeacoffee.com/vassilis"><img src="https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png" alt="SmartIR Climate"></a>
</p>