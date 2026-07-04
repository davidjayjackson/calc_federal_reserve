# FRED (Federal Reserve Bank of St. Louis Economic Data) lookups, exposed
# as Calc spreadsheet functions via a real UNO Add-In (so they appear in
# the Function Wizard and autocomplete). See README.md for setup.
#
# FRED.VALUE(series_id; [date])
# FRED.DESCRIPTION(series_id; [field])
#
# API docs: https://fred.stlouisfed.org/docs/api/fred/

import datetime
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import unohelper

from com.sun.star.sheet import XAddIn
from com.sun.star.lang import XServiceName
from com.example.fred import XFred

ADDIN_SERVICE = "com.sun.star.sheet.AddIn"
SERVICE_NAME = "com.example.fred.FredImpl"
IMPL_NAME = "com.example.fred.FredImpl.python"

API_BASE = "https://api.stlouisfed.org/fred"
REQUEST_TIMEOUT = 10

# Calc's default date epoch (day 0 = 1899-12-30), used to convert a date
# cell's numeric serial value into a calendar date.
CALC_EPOCH = datetime.date(1899, 12, 30)

# Observations and metadata change at most once a day, so a short in-memory
# cache keeps a sheet full of FRED formulas from re-hitting the API (and its
# rate limit) on every recalculation.
OBSERVATIONS_CACHE_TTL = 300
METADATA_CACHE_TTL = 3600

DESCRIPTION_FIELDS = (
    "title",
    "units",
    "units_short",
    "frequency",
    "frequency_short",
    "seasonal_adjustment",
    "seasonal_adjustment_short",
    "notes",
    "last_updated",
    "observation_start",
    "observation_end",
    "popularity",
)


class FredError(ValueError):
    """Raised for invalid FRED arguments or API errors."""


_cache = {}


def _cached_get(url, ttl):
    now = time.time()
    hit = _cache.get(url)
    if hit and now - hit[0] < ttl:
        return hit[1]

    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode("utf-8"))
            msg = body.get("error_message", str(e))
        except Exception:
            msg = str(e)
        raise FredError("FRED API error: %s" % msg) from e
    except urllib.error.URLError as e:
        raise FredError("could not reach FRED API: %s" % e.reason) from e

    _cache[url] = (now, data)
    return data


def _resolve_api_key(explicit):
    """Uses the api_key formula argument if given, else FRED_API_KEY."""
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise FredError(
            "no API key: pass one as the api_key argument, or set the "
            "FRED_API_KEY environment variable LibreOffice is launched "
            "with. Get a free key at "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    return key


def _as_iso_date(value):
    """Coerces an optional Calc date argument (serial number, or an
    'YYYY-MM-DD' string) to an ISO date string, or None if omitted."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return (CALC_EPOCH + datetime.timedelta(days=int(value))).isoformat()
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
        return value.strip()
    raise FredError("date must be a date value or an 'YYYY-MM-DD' string")


def _fetch_value(series_id, iso_date, api_key):
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": "10",
    }
    if iso_date:
        params["observation_end"] = iso_date
    url = "%s/series/observations?%s" % (API_BASE, urllib.parse.urlencode(params))
    data = _cached_get(url, OBSERVATIONS_CACHE_TTL)

    for obs in data.get("observations", []):
        # FRED marks missing/not-yet-released observations with ".".
        if obs.get("value") not in (None, "."):
            return float(obs["value"])

    where = " on or before %s" % iso_date if iso_date else ""
    raise FredError("no observations found for series '%s'%s" % (series_id, where))


def _fetch_description(series_id, field, api_key):
    field = (field or "title").strip().lower()
    if field not in DESCRIPTION_FIELDS:
        raise FredError("field must be one of: %s" % ", ".join(DESCRIPTION_FIELDS))

    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    url = "%s/series?%s" % (API_BASE, urllib.parse.urlencode(params))
    data = _cached_get(url, METADATA_CACHE_TTL)

    seriess = data.get("seriess") or []
    if not seriess:
        raise FredError("series '%s' not found" % series_id)
    return str(seriess[0].get(field, ""))


class FredAddIn(unohelper.Base, XFred, XAddIn, XServiceName):
    """Implementation of the FRED.VALUE / FRED.DESCRIPTION spreadsheet functions."""

    def __init__(self, ctx):
        self.ctx = ctx
        self._locale = None

    # --- XFred ------------------------------------------------------------
    def value(self, seriesId, date, apiKey):
        return _fetch_value(
            seriesId.strip().upper(), _as_iso_date(date), _resolve_api_key(apiKey))

    def description(self, seriesId, field, apiKey):
        return _fetch_description(
            seriesId.strip().upper(), field, _resolve_api_key(apiKey))

    # --- XAddIn -------------------------------------------------------------
    # Function/argument metadata is supplied by CalcAddIns.xcu, so these
    # return the programmatic names (or empty strings) as a safe fallback.
    def getProgrammaticFuntionName(self, aDisplayName):  # UNO API spelling
        names = {"FRED.VALUE": "value", "FRED.DESCRIPTION": "description"}
        return names.get(aDisplayName, "")

    def getDisplayFunctionName(self, aProgrammaticName):
        names = {"value": "FRED.VALUE", "description": "FRED.DESCRIPTION"}
        return names.get(aProgrammaticName, "")

    def getFunctionDescription(self, aProgrammaticName):
        descs = {
            "value": "Looks up a FRED series observation, on or before an optional date.",
            "description": "Looks up a metadata field describing a FRED series.",
        }
        return descs.get(aProgrammaticName, "")

    def getDisplayArgumentName(self, aProgrammaticName, nArgument):
        names = {
            "value": ("series_id", "date", "api_key"),
            "description": ("series_id", "field", "api_key"),
        }
        args = names.get(aProgrammaticName, ())
        return args[nArgument] if 0 <= nArgument < len(args) else ""

    def getArgumentDescription(self, aProgrammaticName, nArgument):
        api_key_desc = (
            "Optional. A FRED API key. Defaults to the FRED_API_KEY environment variable."
        )
        descs = {
            "value": (
                "The FRED series ID, e.g. \"GDP\", \"UNRATE\", \"CPIAUCSL\".",
                "Optional. Returns the most recent observation on or before this date. "
                "Defaults to the most recent available observation.",
                api_key_desc,
            ),
            "description": (
                "The FRED series ID, e.g. \"GDP\", \"UNRATE\", \"CPIAUCSL\".",
                "Optional. Metadata field: title (default), units, units_short, frequency, "
                "frequency_short, seasonal_adjustment, seasonal_adjustment_short, notes, "
                "last_updated, observation_start, observation_end, popularity.",
                api_key_desc,
            ),
        }
        args = descs.get(aProgrammaticName, ())
        return args[nArgument] if 0 <= nArgument < len(args) else ""

    def getProgrammaticCategoryName(self, aProgrammaticName):
        return "Add-In"

    def getDisplayCategoryName(self, aProgrammaticName):
        return "Add-In"

    # --- XLocalizable (base of XAddIn) ----------------------------------
    def setLocale(self, aLocale):
        self._locale = aLocale

    def getLocale(self):
        return self._locale

    # --- XServiceName -----------------------------------------------------
    def getServiceName(self):
        return SERVICE_NAME


# --- component registration ----------------------------------------------
g_ImplementationHelper = unohelper.ImplementationHelper()
g_ImplementationHelper.addImplementation(
    FredAddIn,
    IMPL_NAME,
    (SERVICE_NAME, ADDIN_SERVICE),
)
