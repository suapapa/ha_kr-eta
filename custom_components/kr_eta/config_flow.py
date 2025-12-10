from copy import deepcopy
import logging
from typing import Any, Dict, Optional
from urllib.parse import unquote_plus

from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_registry import (
    async_entries_for_config_entry,
    async_get,
)
import voluptuous as vol

from .const import *
from .vworld import GeoCoder

_LOGGER = logging.getLogger(__name__)

AUTH_SCHEMA = vol.Schema({
    vol.Required(CONF_VWORLD_API_KEY): cv.string,
    vol.Required(CONF_KAKAODEVELOPERS_API_KEY): cv.string,
})

STARTPOINT_SCHEMA = vol.Schema({
    vol.Optional(CONF_LOCATION_NAME): cv.string,
    vol.Required(CONF_LOCATION_ADDRESS): cv.string,
})

ENDPOINT_SCHEMA = vol.Schema({
    vol.Optional(CONF_LOCATION_NAME): cv.string,
    vol.Required(CONF_LOCATION_ADDRESS): cv.string,
    vol.Optional(CONF_ADD_WAYPOINT, default=False): cv.boolean,
})

WAYPOINT_SCHEMA = vol.Schema({
    vol.Optional(CONF_LOCATION_NAME): cv.string,
    vol.Required(CONF_LOCATION_ADDRESS): cv.string,
    vol.Optional(CONF_ADD_WAYPOINT, default=False): cv.boolean,
})

class GithubCustomConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Github Custom config flow."""

    data: Optional[Dict[str, Any]]
    gc: GeoCoder

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        
        # Check if there are existing entries to reuse API keys from
        existing_entries = self.hass.config_entries.async_entries(DOMAIN)
        if existing_entries:
            # Reuse keys from the first entry found
            first_entry = existing_entries[0]
            vworld_key = first_entry.data.get(CONF_VWORLD_API_KEY)
            kakao_key = first_entry.data.get(CONF_KAKAODEVELOPERS_API_KEY)
            
            if vworld_key and kakao_key:
                self.data = {
                    CONF_VWORLD_API_KEY: vworld_key,
                    CONF_KAKAODEVELOPERS_API_KEY: kakao_key,
                    CONF_WAYPOINTS: []
                }
                self.gc = GeoCoder(vworld_key, async_get_clientsession(self.hass))
                return await self.async_step_start_location()

        if user_input is not None:
            if not user_input.get(CONF_VWORLD_API_KEY) or not user_input.get(CONF_KAKAODEVELOPERS_API_KEY):
                errors["base"] = "need_api_keys"
            if not errors:
                self.data = user_input
                self.data[CONF_WAYPOINTS] = []
                self.gc = GeoCoder(user_input.get(CONF_VWORLD_API_KEY), async_get_clientsession(self.hass))
                return await self.async_step_start_location()

        return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA, errors=errors)

    async def async_step_start_location(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step: Select start location."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_LOCATION_ADDRESS):
                errors["base"] = "need_address"
            else:
                try:
                    x, y = await self.gc.getcoord(unquote_plus(user_input.get(CONF_LOCATION_ADDRESS)))
                except Exception as e:
                    _LOGGER.exception("Failed to get start location coordinates")
                    errors["base"] = "address_not_found"

            if not errors:
                self.data[CONF_STARTPOINT] = user_input
                self.data[CONF_STARTPOINT][CONF_LOCATION_X] = x
                self.data[CONF_STARTPOINT][CONF_LOCATION_Y] = y
                return await self.async_step_endpoint_location()

        return self.async_show_form(step_id="start_location", data_schema=STARTPOINT_SCHEMA, errors=errors)

    async def async_step_endpoint_location(self, user_input: Optional[Dict[str, Any]] = None):
        """Third step: Select endpoint location."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_LOCATION_ADDRESS):
                errors["base"] = "need_address"
            else:
                try:
                    x, y = await self.gc.getcoord(unquote_plus(user_input.get(CONF_LOCATION_ADDRESS)))
                except Exception as e:
                    _LOGGER.exception("Failed to get endpoint location coordinates")
                    errors["base"] = "address_not_found"

            if not errors:
                self.data[CONF_ENDPOINT] = user_input
                self.data[CONF_ENDPOINT][CONF_LOCATION_X] = x
                self.data[CONF_ENDPOINT][CONF_LOCATION_Y] = y

                if user_input.get(CONF_ADD_WAYPOINT, False):
                    return await self.async_step_waypoint_location()
                
                return self.async_create_entry(title="KR ETA", data=self.data)

        return self.async_show_form(step_id="endpoint_location", data_schema=ENDPOINT_SCHEMA, errors=errors)

    async def async_step_waypoint_location(self, user_input: Optional[Dict[str, Any]] = None):
        """Fourth step: Select waypoint location."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if len(self.data[CONF_WAYPOINTS]) >= 5:
                errors["base"] = "max_waypoints"
            elif not user_input.get(CONF_LOCATION_ADDRESS):
                errors["base"] = "need_address"
            else:
                try:
                    x, y = await self.gc.getcoord(unquote_plus(user_input.get(CONF_LOCATION_ADDRESS)))
                except Exception as e:
                    _LOGGER.exception("Failed to get waypoint location coordinates")
                    errors["base"] = "address_not_found"

            if not errors:
                self.data[CONF_WAYPOINTS].append(user_input)
                self.data[CONF_WAYPOINTS][-1][CONF_LOCATION_X] = x
                self.data[CONF_WAYPOINTS][-1][CONF_LOCATION_Y] = y

                if user_input.get(CONF_ADD_WAYPOINT, False):
                    return await self.async_step_waypoint_location()
                
                return self.async_create_entry(title="KR ETA", data=self.data)

        return self.async_show_form(step_id="waypoint_location", data_schema=WAYPOINT_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Manage the options."""
        errors: Dict[str, str] = {}
        
        # Get current waypoints from config entry data
        current_waypoints = self.config_entry.data.get(CONF_WAYPOINTS, [])
        
        if user_input is not None:
            # Filter out the waypoints selected for removal
            remove_indices = user_input.get("remove_waypoints", [])
            new_waypoints = [
                wp for i, wp in enumerate(current_waypoints) 
                if str(i) not in remove_indices
            ]
            
            # Update the config entry
            new_data = self.config_entry.data.copy()
            new_data[CONF_WAYPOINTS] = new_waypoints
            self.hass.config_entries.async_update_entry(self.config_entry, data=new_data)
            
            return self.async_create_entry(title="", data={})

        # Generate options for the multi-select
        options = {
            str(i): f"{wp.get(CONF_LOCATION_ADDRESS)} ({wp.get(CONF_LOCATION_NAME, 'No Name')})"
            for i, wp in enumerate(current_waypoints)
        }

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("remove_waypoints", default=[]): vol.MultiSelect(options)
            }),
            errors=errors
        )