## Climate Component
#### Configuration variables:
**name** (Optional): Name to use in the frontend<br />
**device_id** (Required): ......<br />
**controller_send_service** (Required): ......<br />
**temperature_sensor** (Optional): **entity_id** for a temperature sensor<br />
**humidity_sensor** (Optional): **entity_id** for a humidity sensor<br />

#### Example:
```yaml
climate:
  - platform: smartir
    name: Office AC
    device_id: 1000
    controller_send_service: switch.broadlink_send_packet_192_168_10_59
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
```

#### Available codes for climate devices:
#### Toyotomi
