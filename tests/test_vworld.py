import pytest
from unittest.mock import patch, Mock, AsyncMock
from custom_components.kr_eta.vworld import GeoCoder, Location

@pytest.fixture
def mock_session():
    session = Mock()
    return session

@pytest.fixture
def geocoder(mock_session):
    return GeoCoder("test_api_key", mock_session)

def test_init(geocoder):
    assert geocoder.api_key == "test_api_key"
    assert geocoder.apiurl == "https://api.vworld.kr/req/address?"

@pytest.mark.asyncio
async def test_getcoord_success(geocoder, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "response": {
            "status": "OK",
            "result": {
                "crs": "EPSG:4326",
                "point": {"x": "127.123", "y": "37.123"}
            }
        }
    }
    
    mock_get_ctx = AsyncMock()
    mock_get_ctx.__aenter__.return_value = mock_response
    mock_get_ctx.__aexit__.return_value = None
    
    mock_session.get.return_value = mock_get_ctx

    x, y = await geocoder.getcoord("Some Address")
    
    assert x == "127.123"
    assert y == "37.123"
    mock_session.get.assert_called_once()

@pytest.mark.asyncio
async def test_getcoord_api_error(geocoder, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "response": {
            "status": "ERROR",
            "error": {"text": "Invalid API Key"}
        }
    }
    
    mock_get_ctx = AsyncMock()
    mock_get_ctx.__aenter__.return_value = mock_response
    mock_get_ctx.__aexit__.return_value = None
    
    mock_session.get.return_value = mock_get_ctx

    with pytest.raises(Exception) as excinfo:
        await geocoder.getcoord("Some Address")
    
    assert "VWorld API Error: Invalid API Key" in str(excinfo.value)

@pytest.mark.asyncio
async def test_getcoord_http_error(geocoder, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 404
    
    mock_get_ctx = AsyncMock()
    mock_get_ctx.__aenter__.return_value = mock_response
    mock_get_ctx.__aexit__.return_value = None
    
    mock_session.get.return_value = mock_get_ctx

    with pytest.raises(Exception) as excinfo:
        await geocoder.getcoord("Some Address")
    
    assert "Failed to get coordinate: 404" in str(excinfo.value)

@pytest.mark.asyncio
async def test_getcoord_not_found(geocoder, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "response": {
            "status": "NOT_FOUND",
            "result": None
        }
    }
    
    mock_get_ctx = AsyncMock()
    mock_get_ctx.__aenter__.return_value = mock_response
    mock_get_ctx.__aexit__.return_value = None
    
    mock_session.get.return_value = mock_get_ctx

    with pytest.raises(Exception) as excinfo:
        await geocoder.getcoord("Unknown Address")
    
    assert "Address not found: Unknown Address" in str(excinfo.value)

@pytest.mark.asyncio
async def test_getcoord_unknown_status(geocoder, mock_session):
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {
        "response": {
            "status": "WEIRD_STATUS",
            "result": None
        }
    }
    
    mock_get_ctx = AsyncMock()
    mock_get_ctx.__aenter__.return_value = mock_response
    mock_get_ctx.__aexit__.return_value = None
    
    mock_session.get.return_value = mock_get_ctx

    with pytest.raises(Exception) as excinfo:
        await geocoder.getcoord("Some Address")
    
    assert "Unknown status: WEIRD_STATUS" in str(excinfo.value)

def test_location_init():
    loc = Location("Home", 127.0, 37.0)
    assert loc.name == "Home"
    assert loc.x == 127.0
    assert loc.y == 37.0

def test_location_repr():
    loc = Location("Home", 127.0, 37.0)
    assert repr(loc) == "Location(Home: 127.0, 37.0)"

@pytest.mark.asyncio
async def test_location_from_address():
    mock_geocoder = Mock()
    # Mocking async getcoord
    mock_geocoder.getcoord = AsyncMock(return_value=(127.123, 37.123))
    
    loc = await Location.from_address(mock_geocoder, "Office", "Some Address")
    
    assert loc.name == "Office"
    assert loc.x == 127.123
    assert loc.y == 37.123
    mock_geocoder.getcoord.assert_called_once_with("Some Address")
