<p align="center">
  <a href="Docs/CLIMATE.md"><img src="http://www.tooltip.gr/github_assets/smartir_climate.png" width="400" alt="SmartIR Climate"></a>
</p>

<p align="center">
  <a href="Docs/MEDIA_PLAYER.md"><img src="http://www.tooltip.gr/github_assets/smartir_mediaplayer.png" width="400" alt="SmartIR Media Player"></a>
</p>

## Links
* [SmartIR Chat on Telegram](https://t.me/smartHomeHub)
* [Discussion about SmartIR Climate (Home Assistant Community)](https://community.home-assistant.io/t/smartir-climate-component/)

## Add to custom updater _(Recommended)_
1. Make sure you've the [custom_updater](https://github.com/custom-components/custom_updater) component installed and working.
2. Add a new reference under `component_urls` in your `custom_updater` configuration in `configuration.yaml`.

```yaml
custom_updater:
  component_urls:
    - https://raw.githubusercontent.com/smartHomeHub/SmartIR/master/custom_components.json
```
