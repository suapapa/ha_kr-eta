import logging
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    UnitOfTime,
)

from .const import (
    DOMAIN,
    CONF_VWORLD_API_KEY,
    CONF_KAKAODEVELOPERS_API_KEY,
    CONF_STARTPOINT,
    CONF_ENDPOINT,
    CONF_WAYPOINTS,
    CONF_LOCATION_NAME,
    CONF_LOCATION_ADDRESS,
    CONF_LOCATION_X,
    CONF_LOCATION_Y,
)
from .kakaomobility import Navi
from .vworld import Location

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the KR ETA sensor."""
    config = entry.data
    
    kakao_api_key = config[CONF_KAKAODEVELOPERS_API_KEY]
    
    start_config = config[CONF_STARTPOINT]
    end_config = config[CONF_ENDPOINT]
    waypoints_config = config.get(CONF_WAYPOINTS, [])

    start_point = Location(
        name=start_config.get(CONF_LOCATION_NAME, "Start"),
        x=start_config[CONF_LOCATION_X],
        y=start_config[CONF_LOCATION_Y]
    )
    
    end_point = Location(
        name=end_config.get(CONF_LOCATION_NAME, "End"),
        x=end_config[CONF_LOCATION_X],
        y=end_config[CONF_LOCATION_Y]
    )
    
    waypoints = []
    for wp in waypoints_config:
        waypoints.append(Location(
            name=wp.get(CONF_LOCATION_NAME, "Waypoint"),
            x=wp[CONF_LOCATION_X],
            y=wp[CONF_LOCATION_Y]
        ))

    async_add_entities([KrEtaSensor(kakao_api_key, start_point, end_point, waypoints, entry.entry_id)], True)


class KrEtaSensor(SensorEntity):
    """Representation of a KR ETA Sensor."""

    def __init__(self, api_key, start_point, end_point, waypoints, entry_id):
        """Initialize the sensor."""
        self._navi = Navi(api_key)
        self._navi.set_startpoint(start_point)
        self._navi.set_endpoint(end_point)
        self._navi.set_waypoints(waypoints)
        
        self._start_point = start_point
        self._end_point = end_point
        self._waypoints = waypoints
        self._entry_id = entry_id
        
        self._state = None
        self._attributes = {}
        
        # Unique ID based on entry_id to allow multiple instances
        self._attr_unique_id = f"{entry_id}_eta"
        self._attr_name = f"ETA {start_point.name} -> {end_point.name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfTime.MINUTES

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return "mdi:car"

    def update(self):
        """Fetch new state data for the sensor."""
        try:
            summary = self._navi.get_eta()
            
            # Duration is in seconds, convert to minutes
            duration_seconds = summary.get("duration")
            self._state = round(duration_seconds / 60)
            
            self._attributes = {
                "distance": summary.get("distance"), # meters
                "fare": summary.get("fare"),
                "taxi_fare": summary.get("taxi_fare"),
                "origin": self._start_point.name,
                "destination": self._end_point.name,
                "waypoints_count": len(self._waypoints)
            }
            
        except Exception as e:
            _LOGGER.error("Error updating KR ETA sensor: %s", e)
            self._state = None
