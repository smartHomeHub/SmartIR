## Climate Component
### Configuration variables:
**name** (Optional): Name to use in the frontend<br />
**device_id** (Required): ......<br />
**controller_send_service** (Required): ......<br />
**temperature_sensor** (Optional): **entity_id** for a temperature sensor<br />
**humidity_sensor** (Optional): **entity_id** for a humidity sensor<br />

### Example:
```yaml
climate:
  - platform: smartir
    name: Office AC
    device_id: 1000
    controller_send_service: switch.broadlink_send_packet_192_168_10_59
    temperature_sensor: sensor.temperature
    humidity_sensor: sensor.humidity
```

### Available codes for climate devices:
#### Toyotomi
| Code | Supported Models | Supported Controllers |
| ------------- | ------------- | -------------------------- |
1000|AKIRA GAN/GAG-A128 VL|Broadlink

#### Panasonic
| Code | Supported Models | Supported Controllers |
| ------------- | ------------- | -------------------------- |
1020|CS-CE7HKEW<br>CS-CE9HKEW<br>CS-CE12HKEW<br>CU-CE7HKE<br>CU-CE9HKE<br>CU-CE12HKE|Broadlink
