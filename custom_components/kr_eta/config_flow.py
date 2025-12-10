from copy import deepcopy
import logging
from typing import Any, Dict, Optional, List
from urllib.parse import unquote_plus
import uuid

from homeassistant import config_entries, core
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .const import *
from .const import *

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

class KrEtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """KR ETA config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Invoked when a user initiates a flow via the user interface."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_VWORLD_API_KEY) or not user_input.get(CONF_KAKAODEVELOPERS_API_KEY):
                errors["base"] = "need_api_keys"
            
            if not errors:
                return self.async_create_entry(title="KR ETA", data=user_input)

        return self.async_show_form(step_id="user", data_schema=AUTH_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.temp_route = {}
        self.gc = None

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Manage the options."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["add_route", "remove_route"]
        )

    async def async_step_add_route(self, user_input: Optional[Dict[str, Any]] = None):
        """Start adding a new route - Start Location."""
        self.temp_route = {
            "id": str(uuid.uuid4()),
            CONF_WAYPOINTS: []
        }
        # Initialize GeoCoder with API key from config entry
        from .vworld import GeoCoder
        vworld_key = self.config_entry.data.get(CONF_VWORLD_API_KEY)
        self.gc = GeoCoder(vworld_key, async_get_clientsession(self.hass))
        
        return await self.async_step_start_location()

    async def async_step_start_location(self, user_input: Optional[Dict[str, Any]] = None):
        """Second step: Select start location."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if not user_input.get(CONF_LOCATION_ADDRESS):
                errors["base"] = "need_address"
            else:
                try:
                    x, y = await self.gc.getcoord(unquote_plus(user_input.get(CONF_LOCATION_ADDRESS)))
                    self.temp_route[CONF_STARTPOINT] = user_input
                    self.temp_route[CONF_STARTPOINT][CONF_LOCATION_X] = x
                    self.temp_route[CONF_STARTPOINT][CONF_LOCATION_Y] = y
                    return await self.async_step_endpoint_location()
                except Exception:
                    _LOGGER.exception("Failed to get start location coordinates")
                    errors["base"] = "address_not_found"

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
                    self.temp_route[CONF_ENDPOINT] = user_input
                    self.temp_route[CONF_ENDPOINT][CONF_LOCATION_X] = x
                    self.temp_route[CONF_ENDPOINT][CONF_LOCATION_Y] = y
                    
                    if user_input.get(CONF_ADD_WAYPOINT, False):
                        return await self.async_step_waypoint_location()
                    
                    return self._save_route()
                except Exception:
                    _LOGGER.exception("Failed to get endpoint location coordinates")
                    errors["base"] = "address_not_found"

        return self.async_show_form(step_id="endpoint_location", data_schema=ENDPOINT_SCHEMA, errors=errors)

    async def async_step_waypoint_location(self, user_input: Optional[Dict[str, Any]] = None):
        """Fourth step: Select waypoint location."""
        errors: Dict[str, str] = {}
        if user_input is not None:
            if len(self.temp_route[CONF_WAYPOINTS]) >= 5:
                errors["base"] = "max_waypoints"
            elif not user_input.get(CONF_LOCATION_ADDRESS):
                errors["base"] = "need_address"
            else:
                try:
                    x, y = await self.gc.getcoord(unquote_plus(user_input.get(CONF_LOCATION_ADDRESS)))
                    waypoint = user_input
                    waypoint[CONF_LOCATION_X] = x
                    waypoint[CONF_LOCATION_Y] = y
                    self.temp_route[CONF_WAYPOINTS].append(waypoint)

                    if user_input.get(CONF_ADD_WAYPOINT, False):
                        return await self.async_step_waypoint_location()
                    
                    return self._save_route()
                except Exception:
                    _LOGGER.exception("Failed to get waypoint location coordinates")
                    errors["base"] = "address_not_found"

        return self.async_show_form(step_id="waypoint_location", data_schema=WAYPOINT_SCHEMA, errors=errors)

    def _save_route(self):
        """Save the constructed route to options."""
        # We store routes in options so they persist and are editable
        current_routes = self.config_entry.options.get(CONF_ROUTES, [])
        # If strictly "adding", just append.
        new_routes = current_routes + [self.temp_route]
        
        return self.async_create_entry(title="", data={CONF_ROUTES: new_routes})

    async def async_step_remove_route(self, user_input: Optional[Dict[str, Any]] = None):
        """Remove a route."""
        current_routes = self.config_entry.options.get(CONF_ROUTES, [])
        
        if user_input is not None:
            selected_indices = [int(i) for i in user_input.get("routes", [])]
            new_routes = [
                route for i, route in enumerate(current_routes) 
                if i not in selected_indices
            ]
            return self.async_create_entry(title="", data={CONF_ROUTES: new_routes})

        options = {
            str(i): f"{route[CONF_STARTPOINT][CONF_LOCATION_NAME]} -> {route[CONF_ENDPOINT][CONF_LOCATION_NAME]}"
            for i, route in enumerate(current_routes)
        }
        
        if not options:
             return self.async_abort(reason="no_routes_to_remove")

        return self.async_show_form(
            step_id="remove_route",
            data_schema=vol.Schema({
                vol.Required("routes"): vol.MultiSelect(options)
            })
        )