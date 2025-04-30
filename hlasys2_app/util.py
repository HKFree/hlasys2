from .db import get_db
from urllib import request
from urllib.parse import quote
import json
import enum
import base64
from .config import *
from datetime import datetime, timedelta
from flask import session
from enum import Enum
from copy import deepcopy

# Try importing the configuration file, and exit if not found
try:
    from . import config
except ImportError:
    print("No config.py file")
    exit(1)


class HkfreeRole(int, enum.Enum):
    """
    Enum representing the different roles in the system (VV, SO, PD, KK).
    Each role is associated with an integer value, and has methods to return its
    long name and corresponding API name.
    """
    VV = 0
    SO = 1
    PD = 2
    KK = 3

    @property
    def long_name(self) -> str:
        """
        Return the full name of the role based on its integer value.

        Returns:
            str: The full name of the role (e.g., "Výkoný Výbor Spolku").
        """
        return [
            "Výkoný Výbor Spolku",  # VV
            "Správci Oblastí",       # SO
            "Představenstvo družstva",  # PD
            "Kontrolní komise",      # KK
        ][self]

    @property
    def udb_api_name(self) -> str:
        """
        Return the corresponding API name for the role.

        Returns:
            str: The API name associated with the role (e.g., "VV").
        """
        print("WARNING: Kontrolni komise not yet implemented, simulating")
        return ["VV", "SO", "PŘEDSTAVENSTVO", "KK"][self]


class UserDBData:
    """
    A singleton class that manages cached user role data.
    It fetches data from UserDB API when needed and caches it for a set duration 
    to improve performance by avoiding repeated requests.
    """
    _instance = None
    _last_fetch: datetime = None
    _vv: int = None
    _so: int = None
    _pd: int = None
    _kk: int = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern to ensure only one instance of UserDBData is created.

        Returns:
            UserDBData: The singleton instance of UserDBData.
        """
        if not cls._instance:
            cls._instance = super(UserDBData, cls).__new__(
                cls, *args, **kwargs)
        return cls._instance

    def _fetch_number_of(self, type: HkfreeRole) -> None:
        """
        Fetch the number of users for a specific role from the UserDB API and
        update the internal cached data.

        Args:
            type (HkfreeRole): The role whose user count is to be fetched.

        Returns:
            None
        """
        print(f"> Fetching {type.name} from UserDB")
        req = request.Request(config.USERDB_API_URL + quote(type.udb_api_name))

        # Base64 encode the authentication string
        base64_auth_str = base64.b64encode(
            f"{config.USERDB_API_USER}:{config.USERDB_API_KEY}".encode("utf-8")
        )
        req.add_header("Authorization", f"Basic {base64_auth_str.decode()}")

        # Send the request and parse the response
        with request.urlopen(req) as response:
            body = response.read()
            data = json.loads(body)

        if not data["result"] or data["result"] != "OK":
            return  # Error in fetching data

        # Update the cached data based on the role type
        match type:
            case HkfreeRole.VV:
                self._vv = data["spravci"]
            case HkfreeRole.SO:
                self._so = data["spravci"]
            case HkfreeRole.PD:
                self._pd = data["spravci"]
            case HkfreeRole.KK:
                self._kk = data["spravci"]

    def _refresh(self) -> None:
        """
        Refresh the cached data if it is outdated based on the cache timeout.
        If the data is stale, it will fetch the latest data from UserDB.

        Returns:
            None
        """
        if not self._last_fetch or (datetime.now() - self._last_fetch) > timedelta(
            hours=USERDB_API_CACHE_TIMEOUT_HOURS
        ):
            self._fetch_number_of(HkfreeRole.VV)
            self._fetch_number_of(HkfreeRole.SO)
            self._fetch_number_of(HkfreeRole.PD)
            print("WARNING: Kontrolni komise not yet implemented, simulating")
            self._kk = {}  # Simulating KK data
            self._last_fetch = datetime.now()

    def number_of(self, role: HkfreeRole) -> int:
        """
        Get the number of users for a specific role.
        The method refreshes the cache if necessary.

        Args:
            role (HkfreeRole): The role whose user count is to be fetched.

        Returns:
            int: The number of users associated with the given role.
        """
        self._refresh()
        return len([self._vv, self._so, self._pd, self._kk][role])

    def is_member_of(self, user_id: int, role: HkfreeRole) -> bool:
        """
        Check if a user is a member of a specified role.
        Returns False for KK as it's not yet implemented.

        Args:
            user_id (int): The ID of the user.
            role (HkfreeRole): The role to check membership for.

        Returns:
            bool: True if the user is a member of the given role, False otherwise.
        """
        if role == HkfreeRole.KK:
            return False

        self._refresh()
        members = [self._vv, self._so, self._pd, self._kk][role]
        return user_id in list(members.keys())

    def not_sure_yet(self, voted_for: dict, voted_against: dict, role: HkfreeRole) -> dict:
        """
        Returns a dictionary of users from the given role who have not voted on a proposal.
        Excludes users who have voted for or against the proposal.

        Args:
            voted_for (dict): Users who voted for the proposal.
            voted_against (dict): Users who voted against the proposal.
            role (HkfreeRole): The role of users to check for undecided votes.

        Returns:
            dict: Users who have not voted yet, with user IDs as keys.
        """
        self._refresh()
        deciders = deepcopy([self._vv, self._so, self._pd, self._kk][role])
        all_votes = voted_for + voted_against
        for voter in all_votes:
            try:
                del deciders[str(voter['author_id'])]
            except:
                # It is okay
                pass

        return deciders

    @property
    def num_of_vv(self) -> int:
        """
        Returns:
            int: The number of Výkonný Výbor members.
        """
        return self.number_of(HkfreeRole.VV)

    @property
    def num_of_so(self) -> int:
        """
        Property to get the number of Správci Oblastí members.

        Returns:
            int: The number of SO members.
        """
        return self.number_of(HkfreeRole.SO)

    @property
    def num_of_pd(self) -> int:
        """
        Property to get the number of Představenstvo Družstva members.

        Returns:
            int: The number of PD members.
        """
        return self.number_of(HkfreeRole.PD)

    @property
    def num_of_kk(self) -> int:
        """
        Property to get the number of Kontrolní Komise members.

        Returns:
            int: The number of KK members.
        """
        return self.number_of(HkfreeRole.KK)


# Initialize the userdb_api instance as a singleton
userdb_api = UserDBData()


def can_vote(user_id: int, proposal: dict) -> bool:
    """
    Check if a user can vote on a given proposal.
    A user can vote if they are a member of the role associated with the proposal
    and have not voted yet.

    Args:
        user_id (int): The ID of the user.
        proposal (dict): The proposal dictionary containing 'type' and 'id'.

    Returns:
        bool: True if the user can vote, False otherwise.
    """
    return userdb_api.is_member_of(user_id, proposal['type']) and not user_voted(
        user_id, proposal["id"]
    )


def user_voted(user_id: int, proposal_id: int) -> bool:
    """
    Check if a user has already voted on a given proposal.

    Args:
        user_id (int): The ID of the user.
        proposal_id (int): The ID of the proposal.

    Returns:
        bool: True if the user has voted, False otherwise.
    """
    db = get_db()

    vote = db.execute(
        """SELECT 1 FROM event
           WHERE author_id = :user_id
           AND proposal_id = :proposal_id
           AND decision IS NOT NULL""",
        {"user_id": user_id, "proposal_id": proposal_id},
    ).fetchone()

    return vote is not None


def next_filter(current_filter: str, add: str) -> str:
    """
    Update the current filter by adding or removing a specified role filter.
    If the role is already in the filter, it will be removed, otherwise, it will be added.

    Args:
        current_filter (str): The current filter string.
        add (str): The role to add or remove (e.g., "vv", "so").

    Returns:
        str: The updated filter string.
    """
    next_str = current_filter
    if add in current_filter:
        next_str = next_str.replace(add, "")
    else:
        next_str += add

    return next_str


def overview_filter(current_filter: str) -> str:
    """
    Generate an SQL WHERE clause to filter proposals based on the current role filter.
    Hardcoded roles are represented by 0 (VV), 1 (SO), 2 (PD), and 3 (KK).

    Args:
        current_filter (str): The current filter string, containing role names (e.g.,
                               'vv', 'so', 'pd', 'kk').

    Returns:
        str: The generated SQL WHERE clause based on the current filter.
    """
    sql_str = "WHERE type IN (0, 1, 2, 3) "

    if 'vv' not in current_filter:
        sql_str = sql_str.replace('0, ', '')
    if 'so' not in current_filter:
        sql_str = sql_str.replace('1, ', '')
    if 'pd' not in current_filter:
        sql_str = sql_str.replace('2, ', '')
    if 'kk' not in current_filter:
        sql_str = sql_str.replace('3', '')

    sql_str = sql_str.replace(', )', ')')

    return sql_str


def is_proposal_accepted(voted_for: int, voted_against: int, type: HkfreeRole) -> bool | None:
    """
    Determine if a proposal is accepted based on the votes and the role type.
    The acceptance criteria depend on the role type:
      - VV requires a majority
      - SO requires a two-thirds majority
      - PD requires a majority
      - KK is not yet implemented.

    Args:
        voted_for (int): The number of votes in favor of the proposal.
        voted_against (int): The number of votes against the proposal.
        type (HkfreeRole): The type of role (VV, SO, PD, KK).

    Returns:
        bool | None: True if the proposal is accepted, False if rejected, or None if undecided.
    """
    n_of_deciders = userdb_api.number_of(type)
    total_votes = voted_for + voted_against

    if config.DEBUG:
        print("n_of_deciders", n_of_deciders)
        print("total_votes", total_votes)
        print("voted_for", voted_for)
        print("voted_against", voted_against)

    match type:
        # VV, potřeba nadpoloviční většina
        case HkfreeRole.VV:
            if voted_against > (n_of_deciders / 2):
                return False
            if voted_for > (n_of_deciders / 2):
                return True

        # SO, potřeba nad dvě třetiny
        case HkfreeRole.SO:
            if voted_against > (n_of_deciders * (2 / 3)):
                return False
            if voted_for > (n_of_deciders * (2 / 3)):
                return True

        # Představenstvo, stejně jako VV
        case HkfreeRole.PD:
            if voted_against > (n_of_deciders / 2):
                return False
            if voted_for > (n_of_deciders / 2):
                return True

        # Kontrolní Komise, zatím není implemetováno
        case HkfreeRole.KK:
            print(
                "WARNING: Vote turnout for KK not yet implemented. Resulting in state UNDECIDED")
            return None

    return None
