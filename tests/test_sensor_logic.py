import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add custom_components to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../custom_components')))

# Mock homeassistant modules
sys.modules['homeassistant'] = MagicMock()
sys.modules['homeassistant.components'] = MagicMock()
sys.modules['homeassistant.components.sensor'] = MagicMock()
sys.modules['homeassistant.config_entries'] = MagicMock()
sys.modules['homeassistant.core'] = MagicMock()
sys.modules['homeassistant.helpers'] = MagicMock()
sys.modules['homeassistant.helpers.entity_platform'] = MagicMock()
sys.modules['homeassistant.const'] = MagicMock()

# Mock requests module
sys.modules['requests'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['async_timeout'] = MagicMock()

# Mock voluptuous module
sys.modules['voluptuous'] = MagicMock()

# Setup specific mocks for imports in sensor.py
class MockSensorEntity:
    pass

sys.modules['homeassistant.components.sensor'].SensorEntity = MockSensorEntity

from kr_eta.kakaomobility import Navi
from kr_eta.sensor import KrEtaSensor
from kr_eta.vworld import Location

class TestKrEtaSensor(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_api_key"
        self.start_point = Location("Start", 127.0, 37.0)
        self.end_point = Location("End", 127.1, 37.1)
        self.waypoints = [Location("WP1", 127.05, 37.05)]
        self.entry_id = "test_entry_id"

    @patch('kr_eta.kakaomobility.requests.Session')
    def test_navi_get_eta(self, mock_session):
        # Mock response from Kakao API
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "routes": [{
                "result_code": 0,
                "summary": {
                    "duration": 3600, # 1 hour in seconds
                    "distance": 10000,
                    "fare": {
                        "taxi": 15000,
                        "toll": 2000
                    },
                    "taxi_fare": 15000
                }
            }]
        }
        mock_session.return_value.get.return_value = mock_response

        navi = Navi(self.api_key)
        navi.set_startpoint(self.start_point)
        navi.set_endpoint(self.end_point)
        
        summary = navi.get_eta()
        
        self.assertEqual(summary['duration'], 3600)
        self.assertEqual(summary['distance'], 10000)

    @patch('kr_eta.kakaomobility.Navi.get_eta')
    def test_sensor_update(self, mock_get_eta):
        # Mock Navi.get_eta return value
        mock_get_eta.return_value = {
            "duration": 3600,
            "distance": 10000,
            "fare": {"taxi": 15000},
            "taxi_fare": 15000
        }

        sensor = KrEtaSensor(self.api_key, self.start_point, self.end_point, self.waypoints, self.entry_id, "test_route_id")
        
        # Trigger update
        sensor.update()
        
        # Verify state (minutes)
        self.assertEqual(sensor.native_value, 60)
        
        # Verify attributes
        self.assertEqual(sensor.extra_state_attributes['distance'], 10000)
        self.assertEqual(sensor.extra_state_attributes['origin'], "Start")
        self.assertEqual(sensor.extra_state_attributes['destination'], "End")
        self.assertEqual(sensor.extra_state_attributes['waypoints_count'], 1)

if __name__ == '__main__':
    unittest.main()
