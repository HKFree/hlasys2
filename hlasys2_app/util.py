from urllib import request
import json
import enum
import base64
from datetime import datetime, timedelta

try:
    from . import config
except ImportError:
    print("No config.py file")
    exit(1)

class HkfreeRole(int, enum.Enum):
    VV = 0
    SO = 1
    MEMBER = 2


# TODO: propper error handling
class UserDBData:
    """
    Data cache for fetching the number of SOs or VVs from UserDB.
    We do not want to fetch from UserDB on every single request, since it
    would slow down the app.
    
    Current timeout is set in USERDB_API_CACHE_TIMEOUT
    """
    _instance = None
    _last_access_so: datetime = None
    _last_access_vv: datetime = None
    _so: int = None
    _vv: int = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(UserDBData, cls).__new__(cls, *args, **kwargs)
        return cls._instance
    
    def _fetch_number(self, vv: bool) -> None:
        print(f"> Fetching {'VV' if vv else 'SO'} from UserDB")
        req = request.Request(
            config.USERDB_API_URL + ('VV' if vv else 'SO')
        )

        base64_auth_str = base64.b64encode(f"{config.USERDB_API_USER}:{config.USERDB_API_KEY}".encode('utf-8'))
        req.add_header("Authorization", f"Basic {base64_auth_str.decode()}")

        with request.urlopen(req) as response:
            body = response.read()
            data = json.loads(body)

        if not data['result'] or data['result'] != 'OK':
            # chybicka
            return
        
        if vv:
            self._vv = data['spravci']
            self._last_access_vv = datetime.now()
        else:
            self._so = data['spravci']
            self._last_access_so = datetime.now()

    def _check_validity(self, vv: bool) -> None:
        if vv:
            if not self._last_access_vv: # not cached
                self._fetch_number(vv=True)
            else: # cached
                data_age: timedelta = datetime.now() - self._last_access_vv
                if data_age.seconds > (config.USERDB_API_CACHE_TIMEOUT_HOURS * 3600): # cached but old
                    self._fetch_number(vv=True)
        else:
            if not self._last_access_so: # not cached
                self._fetch_number(vv=False)
            else: # cached
                data_age: timedelta = datetime.now() - self._last_access_so
                if data_age.seconds > (config.USERDB_API_CACHE_TIMEOUT_HOURS * 3600): # cached but old
                    self._fetch_number(vv=False)
   
    @property
    def n_so(self) -> int:
        self._check_validity(False)
        return len(self._so)

    @property
    def n_vv(self) -> int:
        self._check_validity(True)
        return len(self._vv)

    def is_so(self, user_id: int) -> bool:
        self._check_validity(False)
        return user_id in self._so.keys()
    
    def is_vv(self, user_id: int) -> bool:
        self._check_validity(True)
        return user_id in self._vv.keys()


dd = UserDBData()

def num_so() -> int:
    return dd.n_so

def num_vv() -> int:
    return dd.n_vv

def is_so(user_id: int) -> bool:
    return dd.is_so(user_id)

def is_vv(user_id: int) -> bool:
    return dd.is_vv(user_id)
