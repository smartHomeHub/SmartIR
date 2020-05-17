[![](https://img.shields.io/github/v/release/smartHomeHub/SmartIR.svg?style=flat-square)](https://github.com/smartHomeHub/SmartIR/releases/latest) [![](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/custom-components/hacs)

[![buy me a coffee](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/vassilis)

SmartIR is a custom [Home Assistant](https://www.home-assistant.io/) component for controlling AC units, TV sets and fans via Infrared and RF controllers. An IR or RF controller such as Broadlink is required.

The key features of the component are:
* Support for Base64, Broadlink Hex and Pronto codes.
* Support for external temperature and humidity sensors (Climate platform)
* Support for external on/off sensor that monitors whether your device is actually On or Off. This may be a power monitor sensor.
* Support for voice assistants.


## **Supported controllers**
* [Broadlink](https://www.home-assistant.io/integrations/broadlink/)
* [Xiaomi IR Remote (ChuangmiIr)](https://www.home-assistant.io/integrations/remote.xiaomi_miio/)
* [LOOK.in Remote](http://look-in.club/devices/remote)
* [MQTT Publish service](https://www.home-assistant.io/docs/mqtt/service/)

## **Component setup instructions**
1. Create a directory `custom_components` in your Home Assistant configuration directory.
2. Copy `smartir` from this project including **all** files and sub-directories into the directory `custom_components`.

It should look similar to this after installation:
```
.homeassistant/
|-- custom_components/
|   |-- smartir/
|       |-- __init__.py
|       |-- climate.py
|       |-- fan.py
|       |-- media_player.py
|       |-- etc...
```
3. Add the following to your configuration.yaml file.
```yaml
smartir:
```

## **Platform setup instructions**
<p align="center">
  <a href="CLIMATE.md"><img src="assets/smartir_climate.png" width="400" alt="SmartIR Climate"></a>
</p>

<p align="center">
  <a href="MEDIA_PLAYER.md"><img src="assets/smartir_mediaplayer.png" width="400" alt="SmartIR Media Player"></a>
</p>

<p align="center">
  <a href="FAN.md"><img src="assets/smartir_fan.png" width="400" alt="SmartIR Media Player"></a>
</p>

## **Update the component**
The component will check for updates each time HA is restarted. When there is a new version, a Persistent Notification will appear.
Use the services `smartir.check_updates` to manually check for updates and `smartir.update_component` to start the automatic update.
If you would like to get update notifications from the rc branch (Release Candidate), configure SmartIR as follows:
```yaml
smartir:
  update_branch: rc
```

## Links
* [SmartIR Chat on Telegram](https://t.me/smartHomeHub)
* [Discussion about SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/)

### Give this Project a Star :star:
Star this repository if you had fun!
