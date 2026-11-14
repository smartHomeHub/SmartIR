[![](https://img.shields.io/github/v/release/smartHomeHub/SmartIR.svg?style=flat-square)](https://github.com/smartHomeHub/SmartIR/releases/latest) [![](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/custom-components/hacs)

> ### ⚠️ Warning  
> You are free to fork, modify, and use the code in this repository in accordance with the applicable open-source license.  
>  
> **However, the name "SmartIR" must not be used in any capacity**, especially for promoting, rebranding, or distributing your own fork or derivative works.  
>  
> Please respect this guideline to preserve the original project's identity.

## Overview
SmartIR is a custom integration for controlling **climate devices**, **media players**, **fans** and **lights** via infrared controllers.<br>
SmartIR currently supports the following controllers:
* [Broadlink](https://www.home-assistant.io/integrations/broadlink/)
* [Xiaomi IR Remote (ChuangmiIr)](https://www.home-assistant.io/integrations/remote.xiaomi_miio/)
* [LOOK.in Remote](http://look-in.club/devices/remote)
* [ESPHome User-defined service for remote transmitter](https://esphome.io/components/api.html#user-defined-services)
* [MQTT Publish service](https://www.home-assistant.io/docs/mqtt/service/)

More than 120 climate devices are currently supported out-of-the-box, mainly for the Broadlink controller, thanks to our awesome community.<br><br>
Don't forget to **star** the repository if you had fun!<br><br>


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
|       |-- light.py
|       |-- media_player.py
|       |-- etc...
```
**(2)** Add the following to your configuration.yaml file.
```yaml
smartir:
```

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

**(3)** Configure a platform.

### *HACS*
If you want HACS to handle installation and updates, add SmartIR as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories/). In this case, it is recommended that you turn off automatic updates, as above.
<br><br>


## Platform setup instructions
Click on the links below for instructions on how to configure each platform.
* [Climate platform](/docs/CLIMATE.md)
* [Media Player platform](/docs/MEDIA_PLAYER.md)
* [Fan platform](/docs/FAN.md)
* [Light platform](/docs/LIGHT.md)
<br><br>

## Broadlink platform's ZHA Tuya specifics
Since there is a way to convert *Broadlink* format into *Tuya* format, defining `zha.issue_zigbee_cluster_command`'s `service_data` attributes in the `controlled_data` configuration attribute redirects the `Broadlink` platform to *Tuya* devices (ZS06, ZS08, TS1201) using **ZHA**.

It that case, the `controlled_data` configuration attribute must contain the Zigbee command `service_data` dictionnary like this: 
```yaml
climate:
  - platform: smartir
    device_code: 1287
    controller_data: 
      tuya-broadlink-ieee: "xx:xx:xx:xx:xx:xx:xx:xx"
      # endpoint_id: 1
      # cluster_id: 0xe004
      # cluster_type: "in"
      # command: 2
      # command_type: "server"
      # manufacturer: <code>
```

**Note**: the attribute `tuya-broadlink-ieee` device Zigbee address is required whereas the other `service_data` attributes (`endpoint_id`, `cluster_id`, `command`, etc...) are optional.
The commented out examples are the default settings. They correspond to a TS1201 device.

One can also use the additional ``ZHATuyaBroadlink`` platform in code json files.

In that case, an additional `Raw` encoding (compared to the `Broadlink` platform) corresponds to code learned using the device's `IRLearn` command (`endpoint_id:1, cluster_id: 0xe004. type: in, command_id: 1, command_type: server` for a TS1201 device).

In all cases, the `send` is done using the device's `IRSend` command (`endpoint_id:1, cluster_id: 0xe004. type: in, command_id: 2, command_type:server` for a TS1201 device).


## See also
* [Discussion about SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-control-your-climate-tv-and-fan-devices-via-ir-rf-controllers/)
* [Automatic conversion from Broadlink to Tuya #1355](https://github.com/smartHomeHub/SmartIR/issues/1355)
