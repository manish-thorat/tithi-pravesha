#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tithi Pravesha Calculation Engine
==================================
PyJHora-based engine for Tithi Pravesha, birth-chart basics, panchanga,
and muhurta calculations.

This module contains CALCULATIONS ONLY — it takes no input by itself
(no CSV files, no console prompts). All user input comes through the
Streamlit web interface:

    streamlit run tithi_web_app.py

KEY DISTINCTION:
  - Birth place + Birth timezone     -> used to calculate natal tithi
  - Current place + Current timezone -> used to anchor Pravesha to local sunrise

Requirements:
    pip install PyJHora pyswisseph pyqt6 geocoder requests timezonefinder
                reverse_geocode geopy tzdata certifi pytz streamlit
"""

import sys
import time
from datetime import datetime, timezone, timedelta

import pytz

# ── PyJHora ──────────────────────────────────────────────────────────────────
try:
    from jhora.panchanga import drik
    from jhora.panchanga.vratha import tithi_pravesha
    from jhora import utils
except ImportError as e:
    sys.exit(
        f"ERROR: Could not import PyJHora — {e}\n"
        "Install:  pip install PyJHora pyswisseph pyqt6 geocoder requests "
        "timezonefinder reverse_geocode geopy tzdata certifi pytz"
    )

# ── geopy (optional) ──────────────────────────────────────────────────────────
try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderServiceError, GeocoderTimedOut
    _GEOPY_AVAILABLE = True
except ImportError:
    _GEOPY_AVAILABLE = False

# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_AYANAMSA = "LAHIRI"
GEOCODER_UA      = "TithiPravesha/1.0"

# ── Geocoding ─────────────────────────────────────────────────────────────────

def _lookup_in_jhora_cities(place_name):
    """Try PyJHora's bundled city database (no internet needed)."""
    lookup = getattr(utils, "get_place_coordinates", None)
    if lookup is None:
        return None
    try:
        result = lookup(place_name)
        if result and len(result) >= 2:
            return float(result[0]), float(result[1])
    except Exception:
        pass
    return None


def _lookup_via_nominatim(place_name):
    """Fall back to OpenStreetMap Nominatim with Mac SSL fix."""
    if not _GEOPY_AVAILABLE:
        return None
    try:
        import certifi
        from geopy.adapters import RequestsAdapter

        class CertifiedAdapter(RequestsAdapter):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.session.verify = certifi.where()

        geolocator = Nominatim(
            user_agent=GEOCODER_UA,
            adapter_factory=CertifiedAdapter
        )
        time.sleep(1.1)
        loc = geolocator.geocode(place_name, timeout=10)
        if loc:
            return loc.latitude, loc.longitude
    except (GeocoderServiceError, GeocoderTimedOut) as e:
        print(f"    Nominatim error for '{place_name}': {e}")
    except Exception as e:
        print(f"    Geocoding error: {e}")
    return None


def resolve_coordinates(place_name, lat_str, lon_str, label=""):
    """
    Resolve (lat, lon) from place name or explicit coordinates.
    Priority: explicit coords > PyJHora cities db > Nominatim > (0, 0)
    Returns (lat, lon, source_description).
    """
    tag = f"[{label}] " if label else ""

    if lat_str and lon_str:
        try:
            return float(lat_str), float(lon_str), f"{tag}explicit coordinates"
        except ValueError:
            pass

    if place_name and place_name.strip():
        name = place_name.strip()
        coords = _lookup_in_jhora_cities(name)
        if coords:
            return coords[0], coords[1], f"{tag}PyJHora cities db ({name})"
        coords = _lookup_via_nominatim(name)
        if coords:
            return coords[0], coords[1], f"{tag}Nominatim ({name})"
        print(f"    WARNING: Could not resolve '{name}' — using (0, 0)")
    else:
        print(f"    WARNING: No {label or 'place'} specified — using (0, 0)")

    return 0.0, 0.0, f"{tag}default (0, 0)"


# ── Core calculation ──────────────────────────────────────────────────────────

def configure_jhora(ayanamsa=DEFAULT_AYANAMSA):
    drik.set_ayanamsa_mode(ayanamsa)


def local_to_utc(year, month, day, hour, minute, tz_name):
    tz = pytz.timezone(tz_name)
    return tz.localize(datetime(year, month, day, hour, minute)).astimezone(pytz.utc)


def tz_offset_hours(tz_name):
    tz = pytz.timezone(tz_name)
    return datetime.now(tz).utcoffset().total_seconds() / 3600.0


def _parse_pravesha_result(first, tz_hours):
    """
    Parse a single tithi_pravesha result tuple into a UTC datetime.
    Handles decimal hours >= 24 (Hindu day convention).
    """
    s_date         = first[0]
    t_time         = first[1]
    panchanga_desc = first[3] if len(first) > 3 else ""

    res_year, res_month, res_day = s_date[0], s_date[1], s_date[2]
    day_offset = 0

    if isinstance(t_time, str):
        if "(+" in t_time:
            try:
                day_offset = int(t_time.split("(+")[1].split(")")[0])
            except Exception:
                pass
        t_clean = t_time.split("(")[0].strip()
        try:
            t_dt = datetime.strptime(t_clean, "%I:%M:%S %p")
            res_hour, res_min, res_sec = t_dt.hour, t_dt.minute, t_dt.second
        except ValueError:
            parts = t_clean.split(":")
            if len(parts) >= 2:
                raw_hour = int(parts[0])
                res_min  = int(parts[1])
                res_sec  = int(parts[2]) if len(parts) > 2 else 0
                if raw_hour >= 24:
                    day_offset += raw_hour // 24
                    res_hour    = raw_hour % 24
                else:
                    res_hour = raw_hour
            else:
                res_hour, res_min, res_sec = 0, 0, 0
    else:
        if t_time >= 24.0:
            day_offset += int(t_time) // 24
            t_time      = t_time % 24.0
        res_hour = int(t_time)
        res_min  = int((t_time - res_hour) * 60)
        res_sec  = int(((t_time - res_hour) * 60 - res_min) * 60)

    tz   = timezone(timedelta(hours=tz_hours))
    base = datetime(res_year, res_month, res_day,
                    res_hour, res_min, res_sec, tzinfo=tz)
    return (base + timedelta(days=day_offset)).astimezone(pytz.utc),            panchanga_desc.strip()


def _get_sunrise_utc(date_utc, lat, lon, tz_hours):
    """
    Get sunrise time at given location on given date as UTC datetime.
    Uses PyJHora drik.sunrise().
    """
    place = drik.Place("", lat, lon, tz_hours)
    jd    = utils.julian_day_number(
        drik.Date(date_utc.year, date_utc.month, date_utc.day),
        (0, 0, 0)
    )
    try:
        sr = drik.sunrise(jd, place)
        sr_val = sr[0] if hasattr(sr, '__iter__') else sr
        # sr_val is decimal hours in local time
        sr_h = int(sr_val) % 24
        sr_m = int((sr_val - int(sr_val)) * 60)
        local_sr = datetime(date_utc.year, date_utc.month, date_utc.day,
                            sr_h, sr_m, tzinfo=timezone(timedelta(hours=tz_hours)))
        return local_sr.astimezone(pytz.utc)
    except Exception:
        return None


def find_tithi_pravesha_for_person(
    birth_dt_utc,
    birth_tz_hours,
    curr_lat, curr_lon, curr_tz_hours,
    target_year
):
    """
    Find Tithi Pravesha.

    Step 1: Calculate the exact Pravesha UTC moment using BIRTH location.
            This gives the astronomically correct tithi crossing moment.

    Step 2: For current location, find which calendar day that UTC moment
            falls on at LOCAL sunrise — this is the Pravesha date there.

    Returns (pravesha_utc, panchanga_desc)
    """
    # Convert UTC birth time back to local birth time
    birth_local = birth_dt_utc.astimezone(timezone(timedelta(hours=birth_tz_hours)))
    birth_date  = drik.Date(birth_local.year, birth_local.month, birth_local.day)
    birth_time  = (birth_local.hour, birth_local.minute, birth_local.second)
    birth_place = drik.Place("", 0.0, 0.0, birth_tz_hours)

    try:
        results = tithi_pravesha(birth_date, birth_time, birth_place, target_year)
    except Exception as e:
        print(f"    WARNING: tithi_pravesha() raised: {e}")
        return None, ""

    if not results:
        return None, ""

    # Parse the canonical UTC moment from birth location result
    pravesha_utc, panchanga_desc = _parse_pravesha_result(
        results[0], birth_tz_hours
    )

    # If caller wants current location result, find the correct Pravesha day
    if curr_lat != 0.0 or curr_lon != 0.0:
        # Get sunrises for 3 days around the pravesha moment
        sunrises = {}
        for delta in [-1, 0, 1]:
            check = pravesha_utc + timedelta(days=delta)
            sr    = _get_sunrise_utc(check, curr_lat, curr_lon, curr_tz_hours)
            if sr:
                sunrises[delta] = sr

        # Find the Pravesha day using correct Vedic rule:
        #
        # A tithi "belongs" to the day whose sunrise it is active at.
        # The tithi ends at pravesha_utc.
        #
        # Case A: tithi ends AFTER sunrise on day N
        #         → tithi is active at sunrise → day N is Pravesha day
        #
        # Case B: tithi ends BEFORE sunrise on day N
        #         → tithi was active the previous day (day N-1) at its sunrise
        #         → day N-1 is Pravesha day
        #
        # We find the sunrise that is the LAST one BEFORE pravesha_utc ends.
        # That sunrise's day is the Pravesha day.

        chosen_sr = None
        for delta in [0, -1, 1]:
            if delta in sunrises:
                sr = sunrises[delta]
                if sr <= pravesha_utc:
                    # This sunrise is before the tithi ends — valid Pravesha day
                    if chosen_sr is None or sr > chosen_sr:
                        chosen_sr = sr   # pick the latest sunrise before pravesha

        if chosen_sr is None:
            # All sunrises are after pravesha — tithi ended before any sunrise
            # Pravesha day is the day BEFORE the earliest sunrise
            if -1 in sunrises:
                chosen_sr = sunrises[-1]

        if chosen_sr:
            return chosen_sr, panchanga_desc

    return pravesha_utc, panchanga_desc


# ── Tier 2 Birth Chart basics ────────────────────────────────────────────────

RASI_NAMES = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces"
]

RASI_NAMES_SANSKRIT = [
    "Mesha","Vrishabha","Mithuna","Karka","Simha","Kanya",
    "Tula","Vrishchika","Dhanu","Makara","Kumbha","Meena"
]

LUNAR_MONTH_NAMES = [
    "Chaitra","Vaishakha","Jyeshtha","Ashadha","Shravana","Bhadrapada",
    "Ashwina","Kartika","Margashirsha","Pausha","Magha","Phalguna"
]

# 60 Samvatsara names
SAMVATSARA_NAMES = [
    "Prabhava","Vibhava","Shukla","Pramoda","Prajapati","Angira",
    "Shrimukha","Bhava","Yuva","Dhatri","Ishvara","Bahudhanya",
    "Pramathi","Vikrama","Vrisha","Chitrabhanu","Subhanu","Tarana",
    "Parthiva","Vyaya","Sarvajit","Sarvadhari","Virodhi","Vikrita",
    "Khara","Nandana","Vijaya","Jaya","Manmatha","Durmukhi",
    "Hemalamba","Vilamba","Vikari","Sharvari","Plava","Shubhakrit",
    "Shobhana","Krodhi","Vishvavasu","Parabhava","Plavanga","Kilaka",
    "Saumya","Sadharana","Virodhakrit","Paridhavi","Pramadicha","Ananda",
    "Rakshasa","Nala","Pingala","Kalayukti","Siddharthi","Raudra",
    "Durmati","Dundubhi","Rudhirodgari","Raktakshi","Krodhana","Akshaya"
]


def get_birth_chart_basics(birth_dt_utc, birth_tz_hours, b_lat, b_lon):
    """
    Calculate Tier 2 birth chart basics at the birth moment:
      - Janma Nakshatra (Moon's nakshatra at birth)
      - Nakshatra Pada
      - Janma Rasi (Moon sign at birth)
      - Lagna (Ascendant at birth)
      - Lunar month at birth
      - Samvatsara (Hindu year name)

    All calculated at birth place and birth time.
    Returns a dict.
    """
    result = {}
    place = drik.Place("", b_lat, b_lon, birth_tz_hours)

    # Julian Day at birth moment
    birth_local = birth_dt_utc.astimezone(
        __import__('datetime').timezone(
            __import__('datetime').timedelta(hours=birth_tz_hours)
        )
    )
    jd = utils.julian_day_number(
        drik.Date(birth_local.year, birth_local.month, birth_local.day),
        (birth_local.hour, birth_local.minute, birth_local.second)
    )

    # ── Janma Nakshatra ───────────────────────────────────────────────────────
    # nakshatra returns [nak_num, start_time, end_time, fraction_left,
    #                    next_nak_num, next_start, next_end, next_fraction]
    try:
        nak = drik.nakshatra(jd, place)
        nak_num  = nak[0]
        # Pada = which quarter of nakshatra (1..4)
        # Each nakshatra = 13°20', each pada = 3°20'
        # fraction_left tells us how far through the nakshatra we are
        frac_left = nak[3] if len(nak) > 3 else None
        if frac_left is not None:
            frac_done = 1.0 - frac_left
            pada = min(4, int(frac_done * 4) + 1)
        else:
            pada = "?"
        result["janma_nakshatra"]      = _safe_name(NAKSHATRA_NAMES, nak_num)
        result["janma_nakshatra_pada"] = pada
        result["janma_nakshatra_num"]  = int(nak_num)
    except Exception as e:
        result["janma_nakshatra"]      = f"Error ({e})"
        result["janma_nakshatra_pada"] = "?"
        result["janma_nakshatra_num"]  = None

    # ── Janma Rasi (Moon sign) ────────────────────────────────────────────────
    # raasi returns [rasi_num, end_time, fraction_left, ...]
    try:
        ras = drik.raasi(jd, place)
        ras_num = ras[0]
        result["janma_rasi"]           = _safe_name(RASI_NAMES, ras_num)
        result["janma_rasi_sanskrit"]  = _safe_name(RASI_NAMES_SANSKRIT, ras_num)
    except Exception as e:
        result["janma_rasi"]          = f"Error ({e})"
        result["janma_rasi_sanskrit"] = ""

    # ── Lagna (Ascendant) ─────────────────────────────────────────────────────
    # ascendant returns [constellation, longitude, nak_num, pada]
    try:
        asc = drik.ascendant(jd, place)
        asc_rasi = asc[0]
        asc_lon  = asc[1]
        asc_nak  = asc[2] if len(asc) > 2 else None
        asc_pada = asc[3] if len(asc) > 3 else None
        result["lagna"]          = _safe_name(RASI_NAMES, asc_rasi)
        result["lagna_sanskrit"] = _safe_name(RASI_NAMES_SANSKRIT, asc_rasi)
        result["lagna_lon"]      = float(asc_lon) if asc_lon else None
        result["lagna_nak"]      = _safe_name(NAKSHATRA_NAMES, asc_nak) if asc_nak else ""
        result["lagna_pada"]     = int(asc_pada) if asc_pada else ""
    except Exception as e:
        result["lagna"]          = f"Error ({e})"
        result["lagna_sanskrit"] = ""
        result["lagna_lon"]      = None
        result["lagna_nak"]      = ""
        result["lagna_pada"]     = ""

    # ── Lunar Month ───────────────────────────────────────────────────────────
    # lunar_month returns [month_index, is_adhika]
    # month_index: 1=Chaitra .. 12=Phalguna
    try:
        lm = drik.lunar_month(jd, place)
        lm_num   = lm[0]
        is_adhika = lm[1] if len(lm) > 1 else False
        lm_name  = _safe_name(LUNAR_MONTH_NAMES, lm_num)
        result["lunar_month"] = ("Adhika " if is_adhika else "") + lm_name
    except Exception as e:
        result["lunar_month"] = f"Error ({e})"

    # ── Samvatsara ────────────────────────────────────────────────────────────
    # samvatsara returns index 0..59
    # Requires seplm48.se1 ephemeris file — falls back to formula if missing
    try:
        birth_date = drik.Date(birth_local.year, birth_local.month, birth_local.day)
        sv = drik.samvatsara(birth_date, place)
        sv_idx = sv[0] if hasattr(sv, '__iter__') else sv
        result["samvatsara"] = _safe_name(SAMVATSARA_NAMES, int(sv_idx) + 1)
    except Exception:
        # Fallback: approximate Samvatsara from year
        # Cycle of 60 years, epoch year 1987 = index 0 (Prabhava)
        try:
            sv_idx = (birth_local.year - 1987) % 60
            result["samvatsara"] = (
                _safe_name(SAMVATSARA_NAMES, sv_idx + 1) + " (approx)"
            )
        except Exception as e2:
            result["samvatsara"] = f"unavailable ({e2})"

    return result


# ── Tier 3 Muhurta / Auspiciousness ──────────────────────────────────────────

def _to_decimal(t):
    """
    Convert a time value to decimal hours.
    Handles:
      float/int  : already decimal hours (e.g. 7.5 = 07:30)
      str HH:MM:SS or HH:MM : parse and convert
    Returns float or None.
    """
    if t is None:
        return None
    if isinstance(t, (int, float)):
        return float(t)
    if isinstance(t, str):
        parts = t.strip().split(":")
        try:
            h = int(parts[0])
            m = int(parts[1]) if len(parts) > 1 else 0
            s = int(parts[2]) if len(parts) > 2 else 0
            return h + m / 60.0 + s / 3600.0
        except (ValueError, IndexError):
            return None
    return None


def _fmt_hm(t):
    """Format a time value (decimal hours or HH:MM:SS string) as HH:MM."""
    dec = _to_decimal(t)
    if dec is None:
        return "N/A"
    dec = dec % 24   # handle >= 24
    h = int(dec)
    m = int(round((dec - h) * 60))
    if m == 60:
        h += 1
        m = 0
    suffix = " (+1)" if _to_decimal(t) >= 24 else ""
    return f"{h:02d}:{m:02d}{suffix}"


def _fmt_range(start, end):
    """Format a time range as 'HH:MM – HH:MM'."""
    return f"{_fmt_hm(start)} – {_fmt_hm(end)}"


def _in_range_val(t, start, end):
    """Check if time t falls within [start, end] (all decimal hours or strings)."""
    td = _to_decimal(t)
    sd = _to_decimal(start)
    ed = _to_decimal(end)
    if td is None or sd is None or ed is None:
        return False
    if ed >= 24:
        return td >= sd or td <= ed % 24
    return sd <= td <= ed


def get_muhurta(pravesha_dt_utc, birth_tz_hours, b_lat, b_lon):
    """
    Calculate Tier 3 Muhurta / auspiciousness at the Pravesha moment
    at birth location.

    Returns dict with:
      rahu_kalam, gulika_kalam, yamaganda_kalam,
      abhijit_muhurta, brahma_muhurtha, godhuli_muhurtha,
      durmuhurtam, varjyam, amrit_kaalam,
      chandrabalam, chandrashtama_rasi,
      is_pravesha_in_rahu, is_pravesha_in_gulika,
      is_pravesha_in_abhijit
    """
    result = {}
    place = drik.Place("", b_lat, b_lon, birth_tz_hours)

    # Julian Day at Pravesha moment (birth location)
    local_dt = pravesha_dt_utc.astimezone(
        __import__('datetime').timezone(
            __import__('datetime').timedelta(hours=birth_tz_hours)
        )
    )
    jd = utils.julian_day_number(
        drik.Date(local_dt.year, local_dt.month, local_dt.day),
        (local_dt.hour, local_dt.minute, local_dt.second)
    )

    # Current time as decimal hours for overlap checks
    curr_dec = _to_decimal(local_dt.hour + local_dt.minute / 60.0)

    # ── Rahu Kalam ────────────────────────────────────────────────────────────
    try:
        rk = drik.raahu_kaalam(jd, place)
        rk_s, rk_e = rk[0], rk[1]
        result["rahu_kalam"] = _fmt_range(rk_s, rk_e)
        result["in_rahu"]    = _in_range_val(curr_dec, rk_s, rk_e)
    except Exception as e:
        result["rahu_kalam"] = f"N/A ({e})"
        result["in_rahu"]    = False

    # ── Gulika Kalam ──────────────────────────────────────────────────────────
    try:
        gk = drik.gulikai_kaalam(jd, place)
        gk_s, gk_e = gk[0], gk[1]
        result["gulika_kalam"] = _fmt_range(gk_s, gk_e)
        result["in_gulika"]    = _in_range_val(curr_dec, gk_s, gk_e)
    except Exception as e:
        result["gulika_kalam"] = f"N/A ({e})"
        result["in_gulika"]    = False

    # ── Yamaganda Kalam ───────────────────────────────────────────────────────
    try:
        yk = drik.yamaganda_kaalam(jd, place)
        result["yamaganda_kalam"] = _fmt_range(yk[0], yk[1])
    except Exception as e:
        result["yamaganda_kalam"] = f"N/A ({e})"

    # ── Abhijit Muhurta ───────────────────────────────────────────────────────
    try:
        am = drik.abhijit_muhurta(jd, place)
        am_s, am_e = am[0], am[1]
        result["abhijit_muhurta"] = _fmt_range(am_s, am_e)
        result["in_abhijit"]      = _in_range_val(curr_dec, am_s, am_e)
    except Exception as e:
        result["abhijit_muhurta"] = f"N/A ({e})"
        result["in_abhijit"]      = False

    # ── Brahma Muhurtha ───────────────────────────────────────────────────────
    try:
        bm = drik.brahma_muhurtha(jd, place)
        result["brahma_muhurtha"] = _fmt_range(bm[0], bm[1])
    except Exception as e:
        result["brahma_muhurtha"] = f"N/A ({e})"

    # ── Godhuli Muhurtha ──────────────────────────────────────────────────────
    try:
        gm = drik.godhuli_muhurtha(jd, place)
        result["godhuli_muhurtha"] = _fmt_range(gm[0], gm[1])
    except Exception as e:
        result["godhuli_muhurtha"] = f"N/A ({e})"

    # ── Vijaya Muhurtha ───────────────────────────────────────────────────────
    try:
        vm = drik.vijaya_muhurtha(jd, place)
        result["vijaya_muhurtha"] = _fmt_range(vm[0][0], vm[0][1])
    except Exception as e:
        result["vijaya_muhurtha"] = f"N/A ({e})"

    # ── Durmuhurtam ───────────────────────────────────────────────────────────
    try:
        dm = drik.durmuhurtam(jd, place)
        if isinstance(dm, (list, tuple)) and len(dm) >= 2:
            if isinstance(dm[0], (list, tuple)):
                result["durmuhurtam"] = "  |  ".join(
                    _fmt_range(d[0], d[1]) for d in dm
                )
            else:
                result["durmuhurtam"] = _fmt_range(dm[0], dm[1])
        else:
            result["durmuhurtam"] = str(dm)
    except Exception as e:
        result["durmuhurtam"] = f"N/A ({e})"

    # ── Varjyam ───────────────────────────────────────────────────────────────
    try:
        vj = drik.varjyam(jd, place)
        if vj:
            if isinstance(vj[0], (list, tuple)):
                result["varjyam"] = "  |  ".join(
                    _fmt_range(v[0], v[1]) for v in vj
                )
            else:
                result["varjyam"] = _fmt_range(vj[0], vj[1])
        else:
            result["varjyam"] = "None today"
    except Exception as e:
        result["varjyam"] = f"N/A ({e})"

    # ── Amrit Kalam ───────────────────────────────────────────────────────────
    try:
        ak = drik.amrit_kaalam(jd, place)
        if ak:
            result["amrit_kalam"] = "  |  ".join(
                _fmt_range(a[0], a[1]) for a in ak
            )
        else:
            result["amrit_kalam"] = "None today"
    except Exception as e:
        result["amrit_kalam"] = f"N/A ({e})"

    # ── Chandrabalam ──────────────────────────────────────────────────────────
    # Returns list of (rasi, time) where ascendant is in good position from Moon
    try:
        cb = drik.chandrabalam(jd, place)
        if cb:
            parts = []
            for item in cb:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    parts.append(
                        f"{_safe_name(RASI_NAMES, item[0])} upto {_fmt_hm(item[1])}"
                    )
                else:
                    parts.append(_safe_name(RASI_NAMES, item))
            result["chandrabalam"] = "  |  ".join(parts)
        else:
            result["chandrabalam"] = "Not favourable today"
    except Exception as e:
        result["chandrabalam"] = f"N/A ({e})"

    # ── Chandrashtama ─────────────────────────────────────────────────────────
    # Returns (chandrashtama_rasi, next_moon_entry_jd)
    try:
        cs = drik.chandrashtama(jd, place)
        cs_rasi = cs[0] if hasattr(cs, '__iter__') else cs
        result["chandrashtama_rasi"] = _safe_name(RASI_NAMES, cs_rasi)
        # next_moon_jd → when chandrashtama ends
        if len(cs) > 1:
            y, mo, d, h = utils.jd_to_gregorian(cs[1])
            result["chandrashtama_ends"] = (
                f"{int(d):02d}/{int(mo):02d}/{int(y)} {_fmt_hm(h)}"
            )
        else:
            result["chandrashtama_ends"] = "N/A"
    except Exception as e:
        result["chandrashtama_rasi"]  = f"N/A ({e})"
        result["chandrashtama_ends"]  = "N/A"

    # ── Overall auspiciousness flag ───────────────────────────────────────────
    inauspicious = result.get("in_rahu", False) or result.get("in_gulika", False)
    auspicious   = result.get("in_abhijit", False)
    if auspicious:
        result["overall"] = "✅ Pravesha moment falls in Abhijit Muhurta — very auspicious"
    elif inauspicious:
        flags = []
        if result.get("in_rahu"):   flags.append("Rahu Kalam")
        if result.get("in_gulika"): flags.append("Gulika Kalam")
        result["overall"] = f"⚠️  Pravesha moment falls in {', '.join(flags)}"
    else:
        result["overall"] = "🔵 Pravesha moment is neutral"

    return result


# ── Tier 1 Panchanga at Pravesha moment ──────────────────────────────────────

# Nakshatra names (1..27)
NAKSHATRA_NAMES = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira","Ardra",
    "Punarvasu","Pushya","Ashlesha","Magha","Purva Phalguni","Uttara Phalguni",
    "Hasta","Chitra","Swati","Vishakha","Anuradha","Jyeshtha",
    "Mula","Purva Ashadha","Uttara Ashadha","Shravana","Dhanishtha",
    "Shatabhisha","Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

# Yoga names (1..27)
YOGA_NAMES = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana","Atiganda",
    "Sukarma","Dhriti","Shula","Ganda","Vriddhi","Dhruva",
    "Vyaghata","Harshana","Vajra","Siddhi","Vyatipata","Variyan",
    "Parigha","Shiva","Siddha","Sadhya","Shubha","Shukla",
    "Brahma","Indra","Vaidhriti"
]

# Karana names (1..11)
KARANA_NAMES = [
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",
    "Shakuni","Chatushpada","Naga","Kimstughna"
]

# Vara (weekday) names
VARA_NAMES = [
    "Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"
]

def _safe_name(names_list, index):
    """Safely get name from list using 1-based or 0-based index."""
    if index is None:
        return "Unknown"
    idx = int(index)
    # Try 1-based first (most PyJHora functions return 1-based)
    if 1 <= idx <= len(names_list):
        return names_list[idx - 1]
    # Try 0-based
    if 0 <= idx < len(names_list):
        return names_list[idx]
    return f"#{idx}"


def get_pravesha_panchanga(pravesha_dt_utc, place, birth_tz_hours, curr_tz_hours):
    """
    Calculate full Tier 1 Panchanga at the Pravesha moment.

    Returns a dict with:
      nakshatra, nakshatra_pada, yoga, karana, vara,
      sunrise, sunset, chandrashtama flag
    """
    from jhora import utils as _utils

    result = {}

    # Convert Pravesha UTC datetime to Julian Day
    local_dt = pravesha_dt_utc.astimezone(
        __import__('datetime').timezone(
            __import__('datetime').timedelta(hours=curr_tz_hours)
        )
    )
    jd = _utils.julian_day_number(
        drik.Date(local_dt.year, local_dt.month, local_dt.day),
        (local_dt.hour, local_dt.minute, local_dt.second)
    )

    # ── Nakshatra ─────────────────────────────────────────────────────────────
    try:
        nak = drik.nakshatra(jd, place)
        # Returns (nakshatra_number, start_time, end_time) or similar
        nak_num  = nak[0] if hasattr(nak, '__iter__') else nak
        nak_pada = nak[3] if len(nak) > 3 else None
        result["nakshatra"]      = _safe_name(NAKSHATRA_NAMES, nak_num)
        result["nakshatra_pada"] = int(nak_pada) if nak_pada else "?"
        result["nakshatra_end"]  = nak[2] if len(nak) > 2 else None
    except Exception as e:
        result["nakshatra"]      = f"Error ({e})"
        result["nakshatra_pada"] = "?"
        result["nakshatra_end"]  = None

    # ── Yoga ──────────────────────────────────────────────────────────────────
    try:
        yog = drik.yogam(jd, place)
        yog_num = yog[0] if hasattr(yog, '__iter__') else yog
        result["yoga"]     = _safe_name(YOGA_NAMES, yog_num)
        result["yoga_end"] = yog[2] if len(yog) > 2 else None
    except Exception as e:
        result["yoga"]     = f"Error ({e})"
        result["yoga_end"] = None

    # ── Karana ────────────────────────────────────────────────────────────────
    try:
        kar = drik.karana(jd, place)
        kar_num = kar[0] if hasattr(kar, '__iter__') else kar
        result["karana"]     = _safe_name(KARANA_NAMES, kar_num)
        result["karana_end"] = kar[2] if len(kar) > 2 else None
    except Exception as e:
        result["karana"]     = f"Error ({e})"
        result["karana_end"] = None

    # ── Vara (weekday) ────────────────────────────────────────────────────────
    try:
        vara = drik.vaara(jd)
        vara_num = vara[0] if hasattr(vara, '__iter__') else vara
        result["vara"] = _safe_name(VARA_NAMES, vara_num)
    except Exception as e:
        result["vara"] = pravesha_dt_utc.astimezone(
            __import__('pytz').timezone(
                "Etc/GMT" if curr_tz_hours == 0
                else f"Etc/GMT{int(-curr_tz_hours):+d}"
            )
        ).strftime("%A")

    # ── Sunrise / Sunset ──────────────────────────────────────────────────────
    try:
        sr = drik.sunrise(jd, place)
        ss = drik.sunset(jd, place)
        # Returns decimal hours in local time
        def _fmt_time(decimal_hrs):
            if decimal_hrs is None:
                return "N/A"
            h = int(decimal_hrs) % 24
            m = int((decimal_hrs - int(decimal_hrs)) * 60)
            return f"{h:02d}:{m:02d}"
        sr_val = sr[0] if hasattr(sr, '__iter__') else sr
        ss_val = ss[0] if hasattr(ss, '__iter__') else ss
        result["sunrise"] = _fmt_time(sr_val)
        result["sunset"]  = _fmt_time(ss_val)
    except Exception as e:
        result["sunrise"] = "N/A"
        result["sunset"]  = "N/A"

    # ── Chandrashtama ─────────────────────────────────────────────────────────
    # Chandrashtama = Moon in 8th house from natal Moon sign
    # Considered inauspicious for important activities
    try:
        ca = getattr(drik, "chandrashtama", None)
        if ca:
            result["chandrashtama"] = bool(ca(jd, place))
        else:
            result["chandrashtama"] = None   # not available in this version
    except Exception:
        result["chandrashtama"] = None

    return result


def format_end_time(decimal_hrs, label="upto"):
    """Format a decimal hours end time like '18:30'."""
    if decimal_hrs is None:
        return ""
    h = int(decimal_hrs) % 24
    m = int((decimal_hrs - int(decimal_hrs)) * 60)
    return f" ({label} {h:02d}:{m:02d})"


# ── Entry point ───────────────────────────────────────────────────────────────
# This module has no standalone input mode (no CSV, no console prompts).
if __name__ == "__main__":
    sys.exit(
        "This module is the calculation engine only and takes no direct input.\n"
        "Run the web interface instead:\n"
        "    streamlit run tithi_web_app.py"
    )
