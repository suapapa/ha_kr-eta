import requests
from custom_components.kr_eta.vworld import Location


# curl -v -X GET "https://apis-navi.kakaomobility.com/v1/directions?origin=127.10764191124568,37.402464820205246,angle=270&destination=127.11056336672839,37.39419693653072&summary=false&waypoints=127.17354989857544,37.36629687436494&priority=RECOMMEND&car_fuel=GASOLINE&car_hipass=false&alternatives=false&road_details=false" \
#   -H "Authorization: KakaoAK ${REST_API_KEY}" // 카카오디벨로퍼스에서 발급 받은 API 키 값


class Navi:
    def __init__(self, apikey: str):
        self.apikey = apikey
        self.apiurl = "https://apis-navi.kakaomobility.com/v1/directions"
        self.rs = requests.Session()
        self.rs.headers.update({
            "Authorization": f"KakaoAK {apikey}"
        })
        self.startpoint = None
        self.endpoint = None
        self.waypoints = []

    def set_startpoint(self, point: Location):
        self.startpoint = point

    def set_endpoint(self, point: Location):
        self.endpoint = point
        
    def set_waypoints(self, points: list[Location]):
        if len(points) > 5:
            raise ValueError("Waypoints must be less than 5")

        self.waypoints = points

    def _point_to_param_str(self, point: Location):
        ret = f"{point.x},{point.y}"
        if point.name is not None:
            ret += f",name={point.name}"

        return ret

    def get_eta(self):
        if self.startpoint is None or self.endpoint is None:
            raise ValueError("Startpoint or endpoint is not set")

        params = {
            "origin": self._point_to_param_str(self.startpoint),
            "destination": self._point_to_param_str(self.endpoint),
            "priority": "RECOMMEND", # RECOMMEND, TIME, DISTANCE
            "summary": "true",
        }

        if len(self.waypoints) > 0:
            params["waypoints"] = "|".join([self._point_to_param_str(p) for p in self.waypoints])

        response = self.rs.get(self.apiurl, params=params)
        if not response.status_code == 200:
            raise Exception(f"Failed to get eta: {response.status_code}")

        data = response.json().get("routes")[0]
        if not data.get("result_code") == 0:
            raise Exception(f"Failed to get eta: result_code={data.get("result_code")}, result_msg={data.get("result_msg")}")

        return data.get("summary").get("duration")