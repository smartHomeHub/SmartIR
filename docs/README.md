[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

This is a Fork of SmatIR created by CBrochard,

This fork allows the "Tas" encoding. This allows this integration to use codes and commands with devices flashed with Tasamota. I have also included a check for commands that are a python list. If the command is a list, then an MQTT message is sent for each command in the list. This is useful for televisions whic require several IR codes to change Sources. For example to change sources on my Toshiba television, I send a ir code for the press of the "input" buttin, then a code for the number 1-5 corresponding to the source you wich to select. When the source is switched via the home assisitaint interface, the two IR codes are send in succetion resulting in a the change to the correct source.

This is also useful for my protjector in which the power off button must be pressed twice to power off the unit. (A confirmation screen is shown to confirm power off). By including the same code in a list of the two IR code commands, the power off is achived via one press of the power button in the Home Assisitaint inteface.


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
