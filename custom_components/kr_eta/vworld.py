import aiohttp
import async_timeout

class GeoCoder:
    def __init__(self, api_key: str, session: aiohttp.ClientSession):
        self.api_key = api_key
        self.session = session
        self.apiurl = "https://api.vworld.kr/req/address?"

    async def getcoord(self, address: str, crs: str = "epsg:4326"):
        params = {
            "service": "address",
            "request": "getCoord",
            "key": self.api_key,
            "crs": crs,
            "address": address,
            "format": "json",
            "type": "road",
        }
        async with async_timeout.timeout(10):
            async with self.session.get(self.apiurl, params=params) as response:
                if not response.status == 200:
                    raise Exception(f"Failed to get coordinate: {response.status}")

                data = await response.json()
        
        data = data.get('response')
        data_status = data.get('status')
        if data_status == 'OK':
            result = data.get('result')
            return result.get('point').get('x'), result.get('point').get('y')

        if data_status == 'ERROR':
            raise Exception(f"VWorld API Error: {data.get('error').get('text')}")
        elif data_status == 'NOT_FOUND':
            raise Exception(f"Address not found: {address}")
        else:
            raise Exception(f"Unknown status: {data_status}")

class Location:
    def __init__(self, name: str, x: float, y: float):
        self.name = name
        self.x = x
        self.y = y

    @classmethod
    async def from_address(cls, gc: GeoCoder, name: str, addr: str):
        x, y = await gc.getcoord(addr)
        return cls(name, x, y)

    def __repr__(self):
        return f"Location({self.name}: {self.x}, {self.y})"
        