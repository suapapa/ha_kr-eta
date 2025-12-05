import pytest
from unittest.mock import Mock, patch
from custom_components.kr_eta.kakaomobility import Navi
from custom_components.kr_eta.vworld import Location

@pytest.fixture
def navi():
    return Navi("test_api_key")

@pytest.fixture
def location_start():
    return Location("Start", 127.0, 37.0)

@pytest.fixture
def location_end():
    return Location("End", 127.1, 37.1)

def test_init(navi):
    assert navi.apikey == "test_api_key"
    assert navi.apiurl == "https://apis-navi.kakaomobility.com/v1/directions"
    assert navi.rs.headers["Authorization"] == "KakaoAK test_api_key"
    assert navi.startpoint is None
    assert navi.endpoint is None
    assert navi.waypoints == []

def test_set_startpoint(navi, location_start):
    navi.set_startpoint(location_start)
    assert navi.startpoint == location_start

def test_set_endpoint(navi, location_end):
    navi.set_endpoint(location_end)
    assert navi.endpoint == location_end

def test_set_waypoints(navi, location_start):
    points = [location_start] * 5
    navi.set_waypoints(points)
    assert len(navi.waypoints) == 5

    with pytest.raises(ValueError, match="Waypoints must be less than 5"):
        navi.set_waypoints([location_start] * 6)

def test_point_to_param_str(navi, location_start):
    # Test with name
    param_str = navi._point_to_param_str(location_start)
    assert param_str == "127.0,37.0,name=Start"

    # Test without name
    location_no_name = Location(None, 127.0, 37.0)
    param_str = navi._point_to_param_str(location_no_name)
    assert param_str == "127.0,37.0"

def test_get_eta_success(navi, location_start, location_end):
    navi.set_startpoint(location_start)
    navi.set_endpoint(location_end)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "routes": [{
            "result_code": 0,
            "summary": {"duration": 1234}
        }]
    }
    
    # Mock the session object directly
    navi.rs = Mock()
    navi.rs.get.return_value = mock_response

    duration = navi.get_eta()
    assert duration.get("duration") == 1234
    
    navi.rs.get.assert_called_once()
    args, kwargs = navi.rs.get.call_args
    assert args[0] == navi.apiurl
    assert kwargs["params"]["origin"] == "127.0,37.0,name=Start"
    assert kwargs["params"]["destination"] == "127.1,37.1,name=End"

def test_get_eta_with_waypoints(navi, location_start, location_end):
    navi.set_startpoint(location_start)
    navi.set_endpoint(location_end)
    navi.set_waypoints([location_start, location_end])

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "routes": [{
            "result_code": 0,
            "summary": {"duration": 1234}
        }]
    }
    
    navi.rs = Mock()
    navi.rs.get.return_value = mock_response

    navi.get_eta()
    
    _, kwargs = navi.rs.get.call_args
    assert "waypoints" in kwargs["params"]
    assert kwargs["params"]["waypoints"] == "127.0,37.0,name=Start|127.1,37.1,name=End"

def test_get_eta_missing_points(navi, location_start):
    with pytest.raises(ValueError, match="Startpoint or endpoint is not set"):
        navi.get_eta()

    navi.set_startpoint(location_start)
    with pytest.raises(ValueError, match="Startpoint or endpoint is not set"):
        navi.get_eta()

def test_get_eta_http_error(navi, location_start, location_end):
    navi.set_startpoint(location_start)
    navi.set_endpoint(location_end)

    mock_response = Mock()
    mock_response.status_code = 500
    
    navi.rs = Mock()
    navi.rs.get.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get eta: 500"):
        navi.get_eta()

def test_get_eta_api_error(navi, location_start, location_end):
    navi.set_startpoint(location_start)
    navi.set_endpoint(location_end)

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "routes": [{
            "result_code": 101,
            "result_msg": "Some error",
            "summary": {}
        }]
    }
    
    navi.rs = Mock()
    navi.rs.get.return_value = mock_response

    with pytest.raises(Exception, match="Failed to get eta: result_code=101, result_msg=Some error"):
        navi.get_eta()
