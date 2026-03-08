from __future__ import annotations

from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .const import (
    CONF_CONTROLLER_DATA,
    CONF_DELAY,
    CONF_DEVICE_CODE,
    CONF_PLATFORM,
    DEFAULT_DELAY,
    DOMAIN,
    PLATFORM_TITLES,
    PLATFORMS,
)

from .helpers import (
    get_manufacturers,
    get_models_for_manufacturer,
    infer_title,
)

CONF_CONTROLLER = "controller"

CONTROLLERS = [
    "Broadlink",
    "Xiaomi",
    "MQTT",
    "LOOKin",
    "ESPHome",
]


class SmartIRConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input=None):

        if user_input is not None:
            self._data[CONF_PLATFORM] = user_input[CONF_PLATFORM]
            return await self.async_step_manufacturer()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PLATFORM): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[
                                selector.SelectOptionDict(
                                    value=p,
                                    label=PLATFORM_TITLES[p],
                                )
                                for p in PLATFORMS
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )

    async def async_step_manufacturer(self, user_input=None):

        platform = self._data[CONF_PLATFORM]
        manufacturers = get_manufacturers(platform)

        if user_input is not None:
            self._data["manufacturer"] = user_input["manufacturer"]
            return await self.async_step_model()

        return self.async_show_form(
            step_id="manufacturer",
            data_schema=vol.Schema(
                {
                    vol.Required("manufacturer"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=manufacturers,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_model(self, user_input=None):

        platform = self._data[CONF_PLATFORM]
        manufacturer = self._data["manufacturer"]

        models = get_models_for_manufacturer(platform, manufacturer)

        if user_input is not None:
            self._data[CONF_DEVICE_CODE] = int(user_input[CONF_DEVICE_CODE])
            return await self.async_step_controller()

        options = [
            selector.SelectOptionDict(
                value=item["code"],
                label=item["label"],
            )
            for item in models
        ]

        return self.async_show_form(
            step_id="model",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_CODE): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_controller(self, user_input=None):

        if user_input is not None:
            self._data[CONF_CONTROLLER] = user_input[CONF_CONTROLLER]
            return await self.async_step_name()

        return self.async_show_form(
            step_id="controller",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CONTROLLER): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=CONTROLLERS,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_name(self, user_input=None):

        platform = self._data[CONF_PLATFORM]
        code = self._data[CONF_DEVICE_CODE]
        controller = self._data[CONF_CONTROLLER]

        default_name = infer_title(
            {
                "platform": platform,
                "device_code": code,
            }
        )

        if user_input is not None:

            data = {**self._data, **user_input}

            data[CONF_DEVICE_CODE] = int(data[CONF_DEVICE_CODE])
            data[CONF_DELAY] = DEFAULT_DELAY

            data["controller"] = controller
            data["unique_id"] = uuid.uuid4().hex

            await self.async_set_unique_id(data["unique_id"])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=data[CONF_NAME],
                data=data,
            )

        if controller in ["Broadlink", "Xiaomi", "ESPHome"]:
            controller_field = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="remote")
            )
        else:
            controller_field = str

        return self.async_show_form(
            step_id="name",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=default_name): str,
                    vol.Required(CONF_CONTROLLER_DATA): controller_field,
                }
            ),
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return SmartIROptionsFlow()


class SmartIROptionsFlow(config_entries.OptionsFlow):

    async def async_step_init(self, user_input=None):

        data = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME,
                        default=data.get(CONF_NAME, self.config_entry.title),
                    ): str,
                }
            ),
        )