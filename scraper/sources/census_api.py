"""
Census Bureau API — completely free, no key needed.

Provides economic/demographic data by zip code or city:
  - Population, median income, business density
  - Used to estimate market size per city/sector
"""
import os, logging, json
from typing import Dict, Optional

log = logging.getLogger("census_api")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except Exception:
    pass

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")

try:
    import requests as _req
except ImportError:
    from curl_cffi import requests as _req


_ZIP_TO_ZCTA = {}  # cache

CENSUS变量 = {
    "B01003_001E": "population",
    "B19013_001E": "median_household_income",
    "B05012_001E": "foreign_born_population",
    "B08301_001E": "workers_commute_total",
    "B08006_001E": "workers_drive_alone",
    "B24011_001E": "median_earnings",
    "B01002_001E": "median_age",
}

BUSINESS_VARIABLES = {
    "NAICS2017": "naics_code",
    "ESTAB": "establishments",
    "EMP": "employment",
    "PAYANN": "annual_payroll",
    "RCPTOT": "annual_receipts",
}


def get_demographics(zip_code: str = None, state_fips: str = None, county_fips: str = None) -> Dict:
    if not zip_code and not (state_fips and county_fips):
        return {}

    year = 2023
    variables = ",".join(CENSUS变量.keys())

    key_param = f"&key={CENSUS_API_KEY}" if CENSUS_API_KEY else ""

    if zip_code:
        url = f"https://api.census.gov/data/{year}/acs/acs5?get=NAME,{variables}&for=zip%20code%20tabulation%20area:{zip_code}{key_param}"
    elif state_fips and county_fips:
        url = f"https://api.census.gov/data/{year}/acs/acs5?get=NAME,{variables}&for=county:{county_fips}&in=state:{state_fips}{key_param}"
    else:
        return {}

    try:
        r = _req.get(url, timeout=15)
        if r.status_code != 200:
            return {}

        data = r.json()
        if len(data) < 2:
            return {}

        headers = data[0]
        values = data[1]
        result = {}
        for i, header in enumerate(headers):
            if header in CENSUS变量:
                key = CENSUS变量[header]
                try:
                    result[key] = int(values[i]) if values[i] and values[i] != "null" else 0
                except (ValueError, TypeError):
                    result[key] = 0

        return result

    except Exception as e:
        log.debug(f"Census ACS failed: {e}")
        return {}


def get_business_stats(zip_code: str = None, state_fips: str = None, county_fips: str = None) -> Dict:
    year = 2021
    variables = "ESTAB,EMP,PAYANN,RCPTOT"

    key_param = f"&key={CENSUS_API_KEY}" if CENSUS_API_KEY else ""

    if zip_code:
        url = f"https://api.census.gov/data/{year}/ecnbasic?get=NAME,NAICS2017,{variables}&for=zip%20code%20tabulation%20area:{zip_code}{key_param}"
    elif state_fips and county_fips:
        url = f"https://api.census.gov/data/{year}/ecnbasic?get=NAME,NAICS2017,{variables}&for=county:{county_fips}&in=state:{state_fips}{key_param}"
    else:
        return {}

    try:
        r = _req.get(url, timeout=15)
        if r.status_code != 200:
            return {}

        data = r.json()
        if len(data) < 2:
            return {}

        total_estab = 0
        total_emp = 0
        for row in data[1:]:
            try:
                estab = int(row[data[0].index("ESTAB")]) if "ESTAB" in data[0] else 0
                emp = int(row[data[0].index("EMP")]) if "EMP" in data[0] else 0
                total_estab += estab
                total_emp += emp
            except (ValueError, TypeError, IndexError):
                continue

        return {
            "total_establishments": total_estab,
            "total_employment": total_emp,
        }

    except Exception as e:
        log.debug(f"Census business stats failed: {e}")
        return {}


def get_city_demographics(city: str, state: str = "") -> Dict:
    city_state_map = {
        "Miami": ("12", "086"), "Houston": ("48", "201"), "Chicago": ("17", "031"),
        "Dallas": ("48", "113"), "Phoenix": ("04", "013"), "Austin": ("48", "453"),
        "San Diego": ("06", "073"), "Los Angeles": ("06", "037"), "New York": ("36", "061"),
        "Atlanta": ("13", "121"), "Denver": ("08", "031"), "Seattle": ("53", "033"),
        "Tampa": ("12", "057"), "Charlotte": ("37", "119"), "San Antonio": ("48", "029"),
        "Las Vegas": ("32", "003"), "Phoenix": ("04", "013"), "Portland": ("41", "051"),
        "San Francisco": ("06", "075"), "Boston": ("25", "025"), "Philadelphia": ("42", "101"),
        "Washington": ("11", "001"), "Nashville": ("47", "037"), "Orlando": ("12", "095"),
        "Minneapolis": ("27", "053"), "Salt Lake City": ("49", "035"), "Jacksonville": ("12", "031"),
        "Scottsdale": ("04", "013"), "Beverly Hills": ("06", "037"), "Toronto": None,
        "Vancouver": None, "Calgary": None, "Edmonton": None, "Ottawa": None, "Montreal": None,
    }

    key = city
    if key in city_state_map:
        sf = city_state_map[key]
        if sf is None:
            return {}
        state_fips, county_fips = sf
        demo = get_demographics(state_fips=state_fips, county_fips=county_fips)
        biz = get_business_stats(state_fips=state_fips, county_fips=county_fips)
        demo.update(biz)
        demo["city"] = city
        demo["market_source"] = "census"
        return demo

    return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(get_city_demographics("Miami"), indent=2))
