# SmartIR Fujitsu AR-DB1

A SmartIR fork for Fujitsu air conditioners that use the **AR-DB1 remote control**.  In addition to ordinary SmartIR sending, it can receive the IR frame captured by ESPHome and keep the Home Assistant climate entity synchronized when the physical remote is used.

## What this fork adds

- Fujitsu AR-DB1 code file (`7286`) for ESPHome transmitters.
- ESPHome receiver decoding for full state frames and the OFF command.
- State synchronization from the physical remote, scoped to the originating ESPHome device so identical units do not update each other.
- Native Home Assistant vertical swing control.
- Clear `Medium` and `Quiet` fan-mode labels.
- A generic ESPHome example in [`aircon.yaml`](aircon.yaml), including optional diagnostic entities.

## Install with HACS

1. In Home Assistant, open **HACS → Integrations**.
2. Open the three-dot menu, choose **Custom repositories**, then add:
   - Repository: `https://github.com/tsaouste/SmartIR-Fujitsu-ARDB1`
   - Category: **Integration**
3. Find **SmartIR Fujitsu AR-DB1** in HACS and install it.
4. Restart Home Assistant.

If the integration was previously installed from another SmartIR source, remove that installation first so that only one `custom_components/smartir` directory remains.

## ESPHome setup

1. Copy [`aircon.yaml`](aircon.yaml) into your ESPHome configuration directory and give it a device-specific filename if desired.
2. Create a `secrets.yaml` alongside it from [`secrets.example.yaml`](secrets.example.yaml), then provide your Wi-Fi and ESPHome API encryption values.
3. Adjust the board and GPIO pins (`D1`, `D2`, `D5`, `D7`) to match your hardware.
4. Install the ESPHome configuration. Its event name is `esphome.aircon_ir_received`; keep this value aligned with `receiver_event` below if you change it.

## Home Assistant configuration

Add a climate entry to `configuration.yaml` and then restart Home Assistant. Replace the example entity and device ID values with yours. The ESPHome device ID is available in **Developer tools → States** or in a received event.

```yaml
climate:
  - platform: smartir
    name: Office A/C
    unique_id: office_ac
    device_code: 7286
    controller_data: aircon_send_raw_command
    temperature_sensor: sensor.air_condition_current_temperature
    humidity_sensor: sensor.air_condition_current_humidity
    receiver_event: esphome.aircon_ir_received
    receiver_device_id: YOUR_ESPHOME_DEVICE_ID
```

`controller_data` is the ESPHome action name formed from the ESPHome node name and the `send_raw_command` action. For the supplied `aircon.yaml`, it is `aircon_send_raw_command`.

When using more than one air conditioner, use a unique ESPHome node name and `receiver_device_id` for every unit. The same device code (`7286`) may be used for identical AR-DB1 remotes.

## Notes

- The `swing_mode` control represents continuous vertical swing. The AR-DB1's separate fixed-louvre-position button is intentionally not exposed because it reports only a relative next position, not an absolute state.
- The ESPHome diagnostic entities are disabled by default, apart from Wi-Fi signal. They can be enabled from the device page when troubleshooting.
- The custom integration icon is bundled locally and is shown by Home Assistant 2026.3 or newer.
- This is a focused fork of [SmartIR](https://github.com/smartHomeHub/SmartIR); its normal device support remains available.
