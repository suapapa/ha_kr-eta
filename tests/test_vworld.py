import pytest
from unittest.mock import patch, Mock
from custom_components.kr_eta.vworld import GeoCoder

@pytest.fixture
def geocoder():
    return GeoCoder("test_api_key")

def test_init(geocoder):
    assert geocoder.api_key == "test_api_key"
    assert geocoder.apiurl == "https://api.vworld.kr/req/address?"

@patch("custom_components.kr_eta.vworld.requests.get")
def test_getcoord_success(mock_get, geocoder):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": {
            "status": "OK",
            "result": {
                "crs": "EPSG:4326",
                "point": {"x": "127.123", "y": "37.123"}
            }
        }
    }
    mock_get.return_value = mock_response

    x, y = geocoder.getcoord("Some Address")
    
    assert x == "127.123"
    assert y == "37.123"
    mock_get.assert_called_once()

@patch("custom_components.kr_eta.vworld.requests.get")
def test_getcoord_api_error(mock_get, geocoder):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": {
            "status": "ERROR",
            "error": {"text": "Invalid API Key"}
        }
    }
    mock_get.return_value = mock_response

    with pytest.raises(Exception) as excinfo:
        geocoder.getcoord("Some Address")
    
    assert "World API Error: Invalid API Key" in str(excinfo.value)

@patch("custom_components.kr_eta.vworld.requests.get")
def test_getcoord_http_error(mock_get, geocoder):
    mock_response = Mock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    with pytest.raises(Exception) as excinfo:
        geocoder.getcoord("Some Address")
    
    assert "Failed to get coordinate: 404" in str(excinfo.value)

@patch("custom_components.kr_eta.vworld.requests.get")
def test_getcoord_not_found(mock_get, geocoder):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": {
            "status": "NOT_FOUND",
            "result": None
        }
    }
    mock_get.return_value = mock_response

    with pytest.raises(Exception) as excinfo:
        geocoder.getcoord("Unknown Address")
    
    assert "Address not found: Unknown Address" in str(excinfo.value)

@patch("custom_components.kr_eta.vworld.requests.get")
def test_getcoord_unknown_status(mock_get, geocoder):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "response": {
            "status": "WEIRD_STATUS",
            "result": None
        }
    }
    mock_get.return_value = mock_response

    with pytest.raises(Exception) as excinfo:
        geocoder.getcoord("Some Address")
    
    assert "Unknown status: WEIRD_STATUS" in str(excinfo.value)

from custom_components.kr_eta.vworld import Location

def test_location_init():
    loc = Location("Home", 127.0, 37.0)
    assert loc.name == "Home"
    assert loc.x == 127.0
    assert loc.y == 37.0

def test_location_repr():
    loc = Location("Home", 127.0, 37.0)
    assert repr(loc) == "Location(Home: 127.0, 37.0)"

def test_location_from_address():
    mock_geocoder = Mock()
    mock_geocoder.getcoord.return_value = (127.123, 37.123)
    
    loc = Location.from_address(mock_geocoder, "Office", "Some Address")
    
    assert loc.name == "Office"
    assert loc.x == 127.123
    assert loc.y == 37.123
    mock_geocoder.getcoord.assert_called_once_with("Some Address")
