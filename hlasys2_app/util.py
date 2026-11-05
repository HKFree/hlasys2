from flask import session

from .db import get_db
from urllib import request
from urllib.parse import quote
import json
import enum
import math
import base64
from .config import *
from datetime import datetime, timedelta
from copy import deepcopy

# Try importing the configuration file, and exit if not found
try:
    from . import config
except ImportError:
    print("No config.py file")
    exit(1)


class HkfreeRole(int, enum.Enum):
    """
    Enum representing the different roles in the system (VV, SO, PD, CS, CD).
    Each role is associated with an integer value, and has methods to return its
    long name and corresponding API name.
    """

    VV = 0
    SO = 1
    PD = 2
    CS = 3
    CD = 4

    @property
    def long_name(self) -> str:
        """
        Return the full name of the role based on its integer value.

        Returns:
            str: The full name of the role (e.g., "Výkoný Výbor Spolku").
        """
        return [
            "Výkoný Výbor Spolku",  # VV
            "Správci Oblastí",  # SO
            "Představenstvo družstva",  # PD
            "Členové spolku",  # CS
            "Členové družstva",  # CD
        ][self]

    @property
    def udb_api_name(self) -> str:
        """
        Return the corresponding API name for the role.

        Returns:
            str: The API name associated with the role (e.g., "VV").
        """
        try:
            return ["VV", "SO", "PŘEDSTAVENSTVO"][self]
        except KeyError:
            print("WARNING: This is not implemented in UserDB API! Returning None")
            return None


class UserDBData:
    """
    A singleton class that manages cached user role data.
    It fetches data from UserDB API when needed and caches it for a set duration
    to improve performance by avoiding repeated requests.
    """

    _instance = None
    _last_fetch: datetime = None
    _vv: dict = None
    _so: dict = None
    _pd: dict = None
    _cs: dict = None
    # Not yet implemented
    _cd: dict = None

    def __new__(cls, *args, **kwargs):
        """
        Singleton pattern to ensure only one instance of UserDBData is created.

        Returns:
            UserDBData: The singleton instance of UserDBData.
        """
        if not cls._instance:
            cls._instance = super(UserDBData, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def _fetch_number_of(self, role_type: HkfreeRole) -> None:
        """
        Fetch the number of users for a specific role from the UserDB API and
        update the internal cached data.

        Args:
            type (HkfreeRole): The role whose user count is to be fetched.

        Returns:
            None
        """
        if not config.USERDB_API_USER or not config.USERDB_API_KEY:
            dev_dict = {str(u["id"]): u["family_name"] for u in config.DEV_USERS}
            match role_type:
                case HkfreeRole.VV:
                    self._vv = dev_dict
                case HkfreeRole.SO:
                    self._so = dev_dict
                case HkfreeRole.PD:
                    self._pd = dev_dict
            print(f"> DEV: filled {role_type.name} from DEV_USERS")
            return

        print(f"> Fetching {role_type.name} from UserDB")
        req = request.Request(config.USERDB_API_URL + quote(role_type.udb_api_name))

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
        match role_type:
            case HkfreeRole.VV:
                self._vv = data["spravci"]
            case HkfreeRole.SO:
                self._so = data["spravci"]
            case HkfreeRole.PD:
                self._pd = data["spravci"]

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
            self._fetch_cs()
            self._last_fetch = datetime.now()
            if config.DEBUG:
                print("DEBUG: ", self.__class__, "called _refresh and needs refresh")

    def _fetch_cs(self) -> None:
        if not config.USERDB_API_USER or not config.USERDB_API_KEY:
            self._cs = {str(u["id"]): u["family_name"] for u in config.DEV_USERS}
            print("> DEV: filled CS from DEV_USERS")
            return

        print(f"> Fetching clenove spolku from UserDB")
        req = request.Request(
            "https://userdb.hkfree.org/userdb/api/hlasys/get-cleny-spolku"
        )

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
            print("ERROR: UserDBData._fetch_cs failed.")
            return  # Error in fetching data

        # Update the cached data based on the role type
        self._cs = data["clenove"]

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
        if role in (HkfreeRole.CD):
            return 0
        return len([self._vv, self._so, self._pd, self._cs][role])

    def get_deciders(self, role: HkfreeRole) -> list:
        """
        Get IDs of users that are currently of specified role

        Args:
            role (HkfreeRole): The role to get IDs for

        Returns:
            list of integers
        """
        self._refresh()
        match role:
            case HkfreeRole.PD:
                return self._pd
            case HkfreeRole.VV:
                return self._vv
            case HkfreeRole.CS:
                return self._cs
            case _:
                print(
                    "WARNING: No other than HkfreeRole.PD, .VV or .CS voting lock implemented! returning empty list"
                )
                return []

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


# Initialize the userdb_api instance as a singleton
userdb_api = UserDBData()


def display_name(real_name: str | None, nick: str | None) -> str:
    """
    Name stored with votes, comments and proposals: "<real name> - <nick>".
    Falls back to whichever one is present, and drops the nick when it merely
    repeats the real name.
    """
    real_name = (real_name or "").strip()
    nick = (nick or "").strip()
    if real_name and nick and real_name.casefold() != nick.casefold():
        return f"{real_name} - {nick}"
    return real_name or nick


def short_name(name: str | None) -> str:
    """
    Real-name part of a stored display name ("<real name> - <nick>"), for
    places too narrow for both. Names without a nick are returned unchanged.
    """
    return (name or "").split(" - ", 1)[0]


def current_user() -> tuple[int, str]:
    """
    The logged-in user as (id, display name).

    hkfree SSO puts the UserDB id in preferred_username, the real name in
    family_name and the nick in given_name.
    """
    profile = session["oidc_auth_profile"]
    name = display_name(profile.get("family_name"), profile.get("given_name"))
    return int(profile["preferred_username"]), name


def can_vote(user_id: int, proposal: dict) -> bool:
    """
    Whether user_id is one of the proposal's deciders.

    Args:
        user_id (int): The ID of the user.
        proposal (dict): Proposal row. 'deciders' may be the raw JSON string or
            an already-parsed dict, because view_proposal parses it in place.

    Returns:
        bool: True if the user is a decider, False otherwise.
    """
    deciders = proposal["deciders"]
    if isinstance(deciders, str):
        deciders = json.loads(deciders)

    # Dict key lookup, never a substring test against the raw JSON - otherwise
    # user 27 would pass for decider 277.
    return str(user_id) in deciders


def can_delete_proposal(user_id: int, proposal: dict) -> bool:
    """
    Whether user_id may soft-delete this proposal.

    Allowed only while the proposal is live and undecided, and only for its
    author or for a decider on a small committee. CS is excluded from the
    decider case on purpose - it has ~116 deciders, which would put deletion of
    somebody else's proposal in far too many hands.

    Args:
        user_id (int): The acting user.
        proposal (dict): Proposal row. 'deciders' may be the raw JSON string or
            an already-parsed dict, because view_proposal parses it in place.

    Returns:
        bool: True if deletion is permitted.
    """
    if proposal["deleted"] is not None or proposal["decided"] is not None:
        return False

    if int(proposal["author_id"]) == int(user_id):
        return True

    # Read through getattr: config.py is bind-mounted read-only in production
    # and will not contain this key on the first deploy.
    decider_types = getattr(config, "DECIDER_DELETE_TYPES", [0, 1, 2])
    if int(proposal["type"]) not in decider_types:
        return False

    return can_vote(user_id, proposal)


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


# Overview filter codes, in the order they are written into the URL.
FILTER_CODES = {
    "pd": HkfreeRole.PD,
    "vv": HkfreeRole.VV,
    "cs": HkfreeRole.CS,
    "so": HkfreeRole.SO,
    "cd": HkfreeRole.CD,
}

# Groups offered as toggle pills on the overview. CD (unused) is still
# accepted in the URL, just not offered.
FILTER_PILLS = ("pd", "vv", "cs", "so")

# Groups selected when the URL has no filter. SO is the archive, off by default.
DEFAULT_FILTER = ("pd", "vv", "cs")

# The archive is shown on its own: turning it on turns the rest off and vice versa.
ARCHIVE_FILTER = "so"


def parse_filter(raw: str) -> list[str]:
    """
    Parse the overview filter from the URL into a list of group codes.

    The filter is a concatenation of two-letter codes (e.g. "pdvv"). Unknown
    codes are ignored. An empty or unparseable filter selects DEFAULT_FILTER.

    Args:
        raw (str): Filter segment of the URL.

    Returns:
        list[str]: Selected codes in FILTER_CODES order, never empty.
    """
    raw = (raw or "").lower()
    chunks = {raw[i:i + 2] for i in range(0, len(raw), 2)}
    selected = [code for code in FILTER_CODES if code in chunks]
    return selected or list(DEFAULT_FILTER)


def filter_to_url(selected: list[str]) -> str:
    """
    Canonical URL form of a selection. The default selection is the empty
    string, so the plain /overview URL is what everybody lands on.
    """
    ordered = [code for code in FILTER_CODES if code in selected]
    if not ordered or set(ordered) == set(DEFAULT_FILTER):
        return ""
    return "".join(ordered)


def toggle_filter(selected: list[str], code: str) -> str:
    """
    URL filter after toggling one group on or off. Turning off the last
    selected group turns all default groups back on. The archive is exclusive:
    turning it on deselects every other group, and turning on any other group
    deselects the archive.

    Args:
        selected (list[str]): Currently selected codes (see parse_filter).
        code (str): The code to toggle.

    Returns:
        str: The new filter for the URL.
    """
    if code == ARCHIVE_FILTER:
        return "" if ARCHIVE_FILTER in selected else ARCHIVE_FILTER
    return filter_to_url(list((set(selected) - {ARCHIVE_FILTER}) ^ {code}))


def overview_filter(selected: list[str]) -> tuple[str, dict]:
    """
    SQL condition restricting proposals to the selected groups.

    Args:
        selected (list[str]): Selected codes (see parse_filter).

    Returns:
        tuple: (condition without WHERE, bound parameters)
    """
    params = {f"type_{i}": int(FILTER_CODES[code]) for i, code in enumerate(selected)}
    placeholders = ", ".join(f":{name}" for name in params)
    return f"p.type IN ({placeholders})", params


def is_proposal_accepted(proposal: dict) -> bool | None:
    if config.DEBUG and False:  # make this only for higher log level
        print("DEBUG: is_proposal_accepted data proposal ", proposal)
    treshold = proposal["acceptance_treshold"]

    n_deciders = len(json.loads(proposal["deciders"]))

    if "votes_for" in proposal.keys() and "votes_against" in proposal.keys():
        n_voted_for = proposal["votes_for"]
        n_voted_against = proposal["votes_against"]
    else:
        n_voted_for = len(proposal["voted_for"])
        n_voted_against = len(proposal["voted_against"])

    if config.DEBUG:
        print(
            f"DEBUG: is_proposal_accepted treshold: {treshold}, n_deciders: {n_deciders}, n_voted_for: {n_voted_for}, n_voted_against: {n_voted_against}"
        )

    if n_voted_against >= treshold:
        return False

    if n_voted_for >= treshold:
        return True

    return None


def get_undecided(proposal: int) -> list:
    deciders: list = deepcopy(proposal["deciders"])

    try:
        for vote in proposal["voted_for"]:
            del deciders[str(vote["author_id"])]

        for vote in proposal["voted_against"]:
            del deciders[str(vote["author_id"])]
    except KeyError:
        # The key does not exist, its fine
        pass

    return deciders


def calculate_acceptance_treshold(form_selection: str, deciders: list):
    n_deciders = len(deciders)
    match form_selection:
        # see forms.py for form_selection source values
        case "0":
            # More than half
            return math.ceil(n_deciders * 0.5)

        case "1":
            # More than two thirds
            return math.ceil(n_deciders * (2 / 3))

        case _:
            print(
                "ERROR: calculate_acceptance_treshold failed with unknown argument form_selection"
            )
            exit


def check_proposal_status(proposal: dict) -> bool:
    db = get_db()
    updated_proposal = db.execute(
        """
        SELECT
            p.id, p.acceptance_treshold, p.deciders,
            COALESCE(SUM(CASE WHEN latest.decision = 1 THEN 1 END), 0) AS votes_for,
            COALESCE(SUM(CASE WHEN latest.decision = 0 THEN 1 END), 0) AS votes_against
        FROM proposal p
        LEFT JOIN (
            SELECT e.proposal_id, e.author_id, e.decision
            FROM event e
            JOIN (
                SELECT author_id, MAX(created) AS max_created
                FROM event
                WHERE proposal_id = :proposal_id AND decision IS NOT NULL
                GROUP BY author_id
            ) latest_ids ON e.author_id = latest_ids.author_id AND e.created = latest_ids.max_created
            WHERE e.proposal_id = :proposal_id AND e.decision IS NOT NULL
        ) latest ON p.id = latest.proposal_id
        WHERE p.id = :proposal_id
        """,
        {"proposal_id": proposal["id"]},
    ).fetchone()

    acceptance = is_proposal_accepted(updated_proposal)
    if acceptance is None:
        return False

    if acceptance:
        db.execute(
            "UPDATE proposal SET decided = (datetime('now','localtime')) WHERE id = :id",
            {"id": updated_proposal["id"]},
        )
        db.execute(
            """INSERT INTO event (proposal_id, author_id, author_name, decision, comment)
               VALUES (:pid, 0, 'Systém', NULL, :comment)""",
            {"pid": updated_proposal["id"], "comment": "Návrh byl schválen"},
        )
        db.commit()
        if config.DEBUG:
            print(f"DEBUG: Locking proposal {updated_proposal['id']} - accepted")
        return True
    else:
        db.execute(
            "UPDATE proposal SET decided = (datetime('now','localtime')) WHERE id = :id",
            {"id": updated_proposal["id"]},
        )
        db.execute(
            """INSERT INTO event (proposal_id, author_id, author_name, decision, comment)
               VALUES (:pid, 0, 'Systém', NULL, :comment)""",
            {"pid": updated_proposal["id"], "comment": "Návrh byl zamítnut"},
        )
        db.commit()
        if config.DEBUG:
            print(f"DEBUG: Locking proposal {updated_proposal['id']} - rejected")
        return True
