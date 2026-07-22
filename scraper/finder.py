"""
FindLeads — Business Finder (curl_cffi)
Multi-source scraper: Overpass API + BizData + DuckDuckGo.
100% free, no API keys, no browser needed.
"""

import json
import os
import re
import html
import time
import random
import logging
from typing import List, Dict, Optional, Tuple
from urllib.parse import quote_plus, urlparse, urljoin

from curl_cffi import requests as cffi_requests

logger = logging.getLogger("finder")


# Pre-cached city bounding boxes (avoids Nominatim DNS issues on VM)
CITY_BBOX_CACHE = {
    "miami": (25.7090517, -80.31976, 25.8557827, -80.139157),
    "miami beach": (25.791, -80.131, 25.876, -80.115),
    "scottsdale": (33.494, -111.926, 33.818, -111.720),
    "phoenix": (33.290, -112.178, 33.678, -111.934),
    "austin": (30.099, -97.868, 30.517, -97.560),
    "houston": (29.524, -95.648, 29.958, -95.010),
    "dallas": (32.620, -96.937, 32.989, -96.645),
    "san antonio": (29.301, -98.696, 29.602, -98.336),
    "denver": (39.614, -105.110, 39.914, -104.599),
    "tampa": (27.892, -82.570, 28.086, -82.357),
    "chicago": (41.644, -87.907, 42.023, -87.524),
    "atlanta": (33.647, -84.516, 33.887, -84.326),
    "los angeles": (33.703, -118.668, 34.337, -118.155),
    "la": (33.703, -118.668, 34.337, -118.155),
    "toronto": (43.581, -79.639, 43.855, -79.116),
    "calgary": (50.843, -114.372, 51.187, -113.819),
    "naples": (26.074, -81.819, 26.258, -81.695),
    "new york": (40.477, -74.259, 40.917, -73.700),
    "san diego": (32.534, -117.289, 33.114, -116.915),
    "las vegas": (36.030, -115.378, 36.286, -115.026),
    "riyadh": (24.550, 46.420, 24.810, 46.850),
    "jeddah": (21.420, 39.120, 21.650, 39.320),
    "dubai": (25.064, 55.131, 25.352, 55.415),
    "abu dhabi": (24.300, 54.330, 24.550, 54.680),
    "abudhabi": (24.300, 54.330, 24.550, 54.680),
    "cairo": (29.896, 31.137, 30.175, 31.521),
    "london": (51.386, -0.351, 51.672, 0.149),
    "manchester": (53.366, -2.415, 53.550, -2.130),
    "birmingham": (52.399, -2.083, 52.541, -1.793),
    "johannesburg": (-26.311, 27.839, -27.776, 28.359),
    "cape town": (-34.038, 18.336, -33.829, 18.656),
    "bangkok": (13.630, 100.401, 13.954, 100.759),
    "singapore": (1.138, 103.612, 1.451, 104.068),
    "kuala lumpur": (3.041, 101.576, 3.306, 101.769),
    "istanbul": (40.805, 28.581, 41.282, 29.298),
    "doha": (25.150, 51.413, 25.430, 51.658),
    "kuwait": (29.117, 47.794, 29.409, 48.150),
    "muscat": (23.507, 58.373, 23.648, 58.660),
    "amman": (31.881, 35.861, 32.036, 36.018),
    "beirut": (33.792, 35.453, 33.929, 35.595),
    "barcelona": (41.320, 2.098, 41.469, 2.230),
    "madrid": (40.349, -3.835, 40.561, -3.585),
    "paris": (48.815, 2.224, 48.902, 2.528),
    "berlin": (52.338, 13.088, 52.675, 13.761),
    "tokyo": (35.508, 139.580, 35.833, 139.930),
    "sydney": (-33.980, 151.101, -33.755, 151.350),
    "melbourne": (-37.951, 144.549, -37.670, 145.069),
    "seattle": (47.490, -122.421, 47.736, -122.224),
    "portland": (45.432, -122.840, 45.652, -122.472),
    "san francisco": (37.703, -122.527, 37.832, -122.358),
    "boston": (42.228, -71.190, 42.397, -70.871),
    "philadelphia": (39.867, -75.279, 40.138, -74.960),
    "washington": (38.791, -77.263, 38.996, -76.909),
    "nashville": (36.084, -86.948, 36.282, -86.648),
    "charlotte": (35.127, -80.988, 35.332, -80.723),
    "miami gardens": (25.902, -80.313, 25.986, -80.200),
    "beverly hills": (34.060, -118.430, 34.090, -118.380),
    "edmonton": (53.400, -113.650, 53.650, -113.350),
    "jacksonville": (30.170, -81.800, 30.450, -81.500),
    "minneapolis": (44.850, -93.400, 45.100, -93.100),
    "montreal": (45.400, -73.650, 45.600, -73.450),
    "new orleans": (29.850, -90.200, 30.100, -89.900),
    "orlando": (28.400, -81.500, 28.650, -81.250),
    "ottawa": (45.300, -75.800, 45.550, -75.550),
    "salt lake city": (40.650, -112.050, 40.850, -111.750),
    "vancouver": (49.200, -123.250, 49.350, -123.000),
}

# Known OSM tags for common business types
OVERPASS_CATEGORY_MAP = {
    "dentist": "amenity=dentist",
    "dental clinic": "amenity=dentist",
    "dental": "amenity=dentist",
    "cosmetic dentist": "amenity=dentist",
    "dental implants": "amenity=dentist",
    "orthodontist": "amenity=dentist",
    "pediatric dentist": "amenity=dentist",
    "endodontist": "amenity=dentist",
    "periodontist": "amenity=dentist",
    "prosthodontist": "amenity=dentist",
    "beauty salon": "amenity=beauty_salon",
    "beauty": "amenity=beauty_salon",
    "hair salon": "shop=hairdresser",
    "hair": "shop=hairdresser",
    "barber": "shop=hairdresser",
    "barbershop": "shop=hairdresser",
    "spa": "amenity=spa",
    "day spa": "amenity=spa",
    "nail salon": "shop=beauty",
    "med spa": "amenity=clinic",
    "medspa": "amenity=clinic",
    "medical spa": "amenity=clinic",
    "plastic surgery": "amenity=clinic",
    "cosmetic surgery": "amenity=clinic",
    "plastic surgeon": "amenity=clinic",
    "cosmetic surgeon": "amenity=clinic",
    "dermatologist": "amenity=clinic",
    "dermatology": "amenity=clinic",
    "clinic": "amenity=clinic",
    "medical clinic": "amenity=clinic",
    "family clinic": "amenity=clinic",
    "urgent care": "amenity=clinic",
    "urgentcare": "amenity=clinic",
    "doctor": "amenity=doctor",
    "physician": "amenity=doctor",
    "family doctor": "amenity=doctor",
    "internal medicine": "amenity=doctor",
    "allergy": "amenity=doctor",
    "allergist": "amenity=doctor",
    "optometrist": "amenity=optometrist",
    "eye doctor": "amenity=optometrist",
    "ophthalmologist": "amenity=optometrist",
    "veterinary": "amenity=veterinary",
    "vet": "amenity=veterinary",
    "animal hospital": "amenity=veterinary",
    "pet groomer": "shop=pet_grooming",
    "solar": "shop=solar_panels",
    "solar panel": "shop=solar_panels",
    "solar panel installer": "shop=solar_panels",
    "solar installer": "shop=solar_panels",
    "solar energy": "shop=solar_panels",
    "hvac": "shop=heating",
    "hvac contractor": "shop=heating",
    "heating and cooling": "shop=heating",
    "air conditioning": "shop=heating",
    "ac repair": "shop=heating",
    "plumber": "craft=plumber",
    "plumbing": "craft=plumber",
    "plumbing service": "craft=plumber",
    "electrician": "craft=electrician",
    "electrical": "craft=electrician",
    "restaurant": "amenity=restaurant",
    "cafe": "amenity=cafe",
    "coffee shop": "amenity=cafe",
    "bakery": "shop=bakery",
    "gym": "leisure=fitness_centre",
    "fitness": "leisure=fitness_centre",
    "fitness center": "leisure=fitness_centre",
    "personal trainer": "leisure=fitness_centre",
    "pharmacy": "amenity=pharmacy",
    "drugstore": "amenity=pharmacy",
    "lawyer": "office=lawyer",
    "attorney": "office=lawyer",
    "personal injury lawyer": "office=lawyer",
    "personal injury attorney": "office=lawyer",
    "criminal lawyer": "office=lawyer",
    "family lawyer": "office=lawyer",
    "immigration lawyer": "office=lawyer",
    "accountant": "office=accountant",
    "accounting": "office=accountant",
    "tax consultant": "office=accountant",
    "tax preparer": "office=accountant",
    "car repair": "shop=car_repair",
    "auto repair": "shop=car_repair",
    "mechanic": "shop=car_repair",
    "auto body": "shop=car_repair",
    "body shop": "shop=car_repair",
    "oil change": "shop=car_repair",
    "tire shop": "shop=car_repair",
    "roofing": "craft=roofer",
    "roofing contractor": "craft=roofer",
    "roof repair": "craft=roofer",
    "landscaping": "craft=landscaping",
    "lawn care": "craft=landscaping",
    "tree service": "craft=landscaping",
    "moving company": "office=moving_company",
    "movers": "office=moving_company",
    "moving service": "office=moving_company",
    "cleaning": "office=cleaning",
    "cleaning service": "office=cleaning",
    "house cleaning": "office=cleaning",
    "office cleaning": "office=cleaning",
    "pest control": "shop=pest_control",
    "real estate": "office=estate_agent",
    "real estate agent": "office=estate_agent",
    "real estate agency": "office=estate_agent",
    "realty": "office=estate_agent",
    "hotel": "tourism=hotel",
    "motel": "tourism=motel",
    "hostel": "tourism=hostel",
    "bed and breakfast": "tourism=hostel",
    "car dealer": "shop=car",
    "tattoo": "shop=tattoo",
    "tattoo shop": "shop=tattoo",
    "tattoo parlor": "shop=tattoo",
    "locksmith": "craft=locksmith",
    "storage": "shop=storage_rental",
    "storage unit": "shop=storage_rental",
    "moving storage": "shop=storage_rental",
    "pet shop": "shop=pet",
    "pet store": "shop=pet",
    "florist": "shop=florist",
    "flower shop": "shop=florist",
    "jewelry": "shop=jewelry",
    "jeweler": "shop=jewelry",
    "shoe repair": "shop=shoe_repair",
    "tailor": "shop=tailor",
    "dry cleaning": "shop=dry_cleaning",
    "laundry": "shop=laundry",
    "event planning": "office=event_planner",
    "wedding planner": "office=event_planner",
    "photographer": "craft=photographer",
    "photography": "craft=photographer",
    "pool": "leisure=swimming_pool",
    "pool builder": "leisure=swimming_pool",
    "swimming pool": "leisure=swimming_pool",
}


def _create_session():
    return cffi_requests.Session(impersonate="chrome120")


HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _geocode_city(city: str) -> Tuple[float, float, float, float, str]:
    """Geocode city. Uses local cache first, falls back to Nominatim."""
    city_key = city.lower().strip()

    # Check local cache first (instant, no DNS needed)
    if city_key in CITY_BBOX_CACHE:
        s, w, n, e = CITY_BBOX_CACHE[city_key]
        logger.info(f"Overpass geocode (cache): {city} -> ({s},{w},{n},{e})")
        return s, w, n, e, city

    # Fallback to Nominatim
    try:
        session = _create_session()
        resp = session.get(
            f"https://nominatim.openstreetmap.org/search?q={quote_plus(city)}&format=json&limit=1",
            headers={"User-Agent": "FindLeadsBot/1.0"},
            timeout=10,
        )
        data = resp.json()
        if not data:
            raise ValueError(f"Could not geocode city: {city}")
        bb = data[0].get("boundingbox", [])
        if len(bb) != 4:
            raise ValueError(f"Invalid bounding box for {city}")
        return float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3]), data[0].get("display_name", city)
    except Exception as e:
        logger.error(f"Geocode failed for '{city}': {e}")
        raise


def _get_osm_tag(business_type: str) -> str:
    """Map business_type to OSM tag for Overpass query."""
    bt = business_type.lower().strip()
    if bt in OVERPASS_CATEGORY_MAP:
        return OVERPASS_CATEGORY_MAP[bt]
    for key, val in OVERPASS_CATEGORY_MAP.items():
        if key in bt or bt in key:
            return val
    return ""


def _search_overpass(city: str, business_type: str, limit: int = 50) -> List[Dict]:
    """
    Search OpenStreetMap Overpass API for businesses.
    Returns list of business dicts with name, phone, website, address.
    100% free, no API key.
    """
    osm_tag = _get_osm_tag(business_type)
    if not osm_tag:
        logger.info(f"No OSM tag for '{business_type}', skipping Overpass")
        return []

    try:
        south, west, north, east, display_name = _geocode_city(city)
        logger.info(f"Overpass geocode: {city} -> ({south},{west},{north},{east})")
    except Exception as e:
        logger.error(f"Geocode failed: {e}")
        return []

    key, val = osm_tag.split("=", 1)
    overpass_query = f"""
[out:json][timeout:10];
(
  node["{key}"="{val}"]({south},{west},{north},{east});
  way["{key}"="{val}"]({south},{west},{north},{east});
);
out center {limit};
"""
    try:
        session = _create_session()
        resp = session.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
            timeout=15,
            headers={"User-Agent": "FindLeadsBot/1.0"},
        )
        if resp.status_code != 200:
            logger.error(f"Overpass HTTP {resp.status_code}")
            return []

        data = resp.json()
        elements = data.get("elements", [])
        logger.info(f"Overpass found: {len(elements)} raw results")

        businesses = []
        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "").strip()
            if not name or len(name) < 3:
                continue

            phone = _validate_phone(tags.get("phone", "") or tags.get("contact:phone", ""))
            website = tags.get("website", "") or tags.get("contact:website", "")
            email = tags.get("email", "") or tags.get("contact:email", "")
            addr = tags.get("addr:street", "")
            if tags.get("addr:housenumber"):
                addr = tags["addr:housenumber"] + " " + addr
            if tags.get("addr:city"):
                addr = (addr + ", " + tags["addr:city"]).strip(", ")
            if tags.get("addr:postcode"):
                addr = addr + " " + tags["addr:postcode"]

            lat = el.get("lat") or el.get("center", {}).get("lat", 0)
            lon = el.get("lon") or el.get("center", {}).get("lon", 0)

            facebook = tags.get("contact:facebook", "") or tags.get("facebook", "")
            instagram = tags.get("contact:instagram", "") or tags.get("instagram", "")
            opening = tags.get("opening_hours", "")

            biz = {
                "name": name,
                "rating": 0,
                "review_count": 0,
                "website": website,
                "phone": phone,
                "address": addr,
                "google_url": "",
                "place_id": "",
                "category": business_type,
                "owner_name": "",
                "email": email,
                "instagram": instagram,
                "facebook": facebook,
                "twitter": "",
                "source": "overpass",
                "lat": lat,
                "lon": lon,
                "opening_hours": opening,
            }
            businesses.append(biz)

        logger.info(f"Overpass parsed: {len(businesses)} businesses")
        return businesses

    except Exception as e:
        logger.error(f"Overpass error: {e}")
        return []


BIZDATA_CATEGORY_MAP = {
    "dentist": "dentist",
    "dental clinic": "dentist",
    "dental": "dentist",
    "cosmetic dentist": "dentist",
    "dental implants": "dentist",
    "doctor": "doctor",
    "clinic": "doctor",
    "med spa": "doctor",
    "medspa": "doctor",
    "medical spa": "doctor",
    "plastic surgery": "doctor",
    "cosmetic surgery": "doctor",
    "hospital": "hospital",
    "pharmacy": "pharmacy",
    "beauty salon": "beauty",
    "beauty": "beauty",
    "hair salon": "hairdresser",
    "hair": "hairdresser",
    "barber": "hairdresser",
    "barbershop": "hairdresser",
    "spa": "beauty",
    "day spa": "beauty",
    "nail salon": "beauty",
    "gym": "gym",
    "fitness": "gym",
    "restaurant": "restaurant",
    "cafe": "cafe",
    "coffee shop": "cafe",
    "bakery": "bakery",
    "florist": "florist",
    "lawyer": "lawyer",
    "attorney": "lawyer",
    "personal injury lawyer": "lawyer",
    "personal injury attorney": "lawyer",
    "accountant": "accountant",
    "accounting": "accountant",
    "tax consultant": "accountant",
    "real estate": "real_estate",
    "real estate agent": "real_estate",
    "car repair": "car_repair",
    "auto repair": "car_repair",
    "mechanic": "car_repair",
    "hvac": "car_repair",
    "plumber": "car_repair",
    "plumbing": "car_repair",
    "electrician": "car_repair",
    "roofing": "car_repair",
    "roofing contractor": "car_repair",
    "solar": "car_repair",
    "solar panel": "car_repair",
    "solar installer": "car_repair",
    "landscaping": "car_repair",
    "moving company": "car_repair",
    "movers": "car_repair",
    "cleaning": "car_repair",
    "cleaning service": "car_repair",
    "pest control": "car_repair",
    "pet shop": "pet_shop",
    "veterinary": "hospital",
    "hotel": "hotel",
    "motel": "hotel",
    "hostel": "hostel",
    "car dealer": "car_dealer",
    "tattoo": "beauty",
    "tattoo shop": "beauty",
    "locksmith": "car_repair",
    "storage": "car_repair",
}


def _search_bizdata(city: str, business_type: str, limit: int = 50) -> List[Dict]:
    """
    Search BizData API (OSM-powered) for businesses.
    Returns list of business dicts. 100% free, no API key.
    """
    bt = business_type.lower().strip()
    bizdata_category = BIZDATA_CATEGORY_MAP.get(bt, "")
    if not bizdata_category:
        for key, val in BIZDATA_CATEGORY_MAP.items():
            if key in bt or bt in key:
                bizdata_category = val
                break
    if not bizdata_category:
        logger.info(f"No BizData category for '{business_type}', skipping")
        return []

    try:
        session = _create_session()
        params = {
            "location": city,
            "category": bizdata_category,
            "limit": min(limit, 50),
        }
        resp = session.get(
            "https://bizdata-web.vercel.app/api/businesses",
            params=params,
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(f"BizData HTTP {resp.status_code}")
            return []

        data = resp.json()
        raw = data.get("businesses", [])
        logger.info(f"BizData found: {len(raw)} raw results")

        businesses = []
        for b in raw:
            name = b.get("name", "").strip()
            if not name or len(name) < 3:
                continue

            biz = {
                "name": name,
                "rating": 0,
                "review_count": 0,
                "website": b.get("website", ""),
                "phone": _validate_phone(b.get("phone", "")),
                "address": b.get("address", ""),
                "google_url": "",
                "place_id": "",
                "category": b.get("category", business_type),
                "owner_name": "",
                "email": b.get("email", ""),
                "instagram": "",
                "facebook": "",
                "twitter": "",
                "source": "bizdata",
                "lat": b.get("lat", 0),
                "lon": b.get("lon", 0),
                "opening_hours": b.get("opening_hours", ""),
            }
            businesses.append(biz)

        logger.info(f"BizData parsed: {len(businesses)} businesses")
        return businesses

    except Exception as e:
        logger.error(f"BizData error: {e}")
        return []


PHONE_REGEX = re.compile(
    r'(?:\+971|00971|971|050|052|055|056|058|02|04|06|07|09)[\s\-]?\d{3,4}[\s\-]?\d{3,4}'
    r'|(?:\+1|001)[\s\-]?\(?[0-9]{3}\)?[\s\-]?[0-9]{3}[\s\-]?[0-9]{4}'
    r'|(?:\+44|0044)[\s\-]?\d{4}[\s\-]?\d{6}'
    r'|(?:\+966|00966|05)[\s\-]?\d{4}[\s\-]?\d{4}'
)


# ════════════════════════════════════════════════════════════════
# MAIN SEARCH
# ════════════════════════════════════════════════════════════════

def search_businesses(city: str, business_type: str, limit: int = 20) -> List[Dict]:
    """
    Search for businesses using multiple sources.
    Priority: businesses with websites (can be enriched).
    """
    logger.info(f"Searching: '{business_type}' in '{city}' (limit={limit})")
    session = _create_session()
    all_businesses = []

    # Source 1: Overpass API (OpenStreetMap direct)
    try:
        overpass_results = _search_overpass(city, business_type, limit * 2)
        all_businesses.extend(overpass_results)
        logger.info(f"Overpass: found {len(overpass_results)} results")
    except Exception as e:
        logger.error(f"Overpass error: {e}")

    # Source 2: BizData API (OSM-powered backup)
    try:
        bizdata_results = _search_bizdata(city, business_type, limit)
        all_businesses.extend(bizdata_results)
        logger.info(f"BizData: found {len(bizdata_results)} results")
    except Exception as e:
        logger.error(f"BizData error: {e}")

    # Source 3: DuckDuckGo HTML search (fallback)
    try:
        query = f"{business_type} in {city} phone number website"
        ddg_results = _search_ddg(session, query, limit)
        all_businesses.extend(ddg_results)
        logger.info(f"DDG: found {len(ddg_results)} results")
    except Exception as e:
        logger.error(f"DDG error: {e}")

    # Deduplicate across all sources
    all_businesses = _deduplicate(all_businesses)
    logger.info(f"After dedup: {len(all_businesses)} unique businesses")

    # For businesses WITHOUT website, try to find one via DDG name search
    for biz in all_businesses:
        if not biz.get("website"):
            try:
                name = biz.get("name", "")
                city_clean = city.split(",")[0].strip()
                q = f'"{name}" {city_clean} official website'
                url = f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"
                resp = session.get(url, headers=HEADERS, timeout=3)
                if resp.status_code == 200:
                    links = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</a>', resp.text, re.DOTALL)
                    skip_domains = ["yelp.com", "facebook.com", "linkedin.com", "wikipedia.org",
                                    "yellowpages.com", "google.com", "bing.com", "instagram.com",
                                    "twitter.com", "bbb.org", "bbb.com", "thumbtack.com",
                                    "homeadvisor.com", "houzz.com", "mapquest.com",
                                    "foursquare.com", "cylex.us.com", "chamberofcommerce.com",
                                    "manta.com", "zoominfo.com", "glassdoor.com", "indeed.com",
                                    "clutch.co", "expertise.com", "bark.com", "apple.com",
                                    "youtube.com", "pinterest.com", "tiktok.com", "nextdoor.com",
                                    "reddit.com", "quora.com", "opendi.us", "superpages.com",
                                    "local.yahoo.com", "us.mylocalservices.com", "mapquest.com",
                                    "hotfrog.com", "merchantcircle.com", "showmelocal.com",
                                    "citysearch.com", "local.com", "dexknows.com",
                                    "n49.com", "boredombreaker.co", "bizapedia.com",
                                    "microsoft.com", "amazon.com", "ebay.com", "etsy.com",
                                    "angieslist.com", "angi.com", "porch.com", "yelp.ca",
                                    "tripadvisor.com", "booking.com", "expedia.com",
                                    "sites.google.com", "wixsite.com", "wordpress.com",
                                    "squarespace.com", "godaddysites.com", "weebly.com",
                                    "411.info", "local.us-info.com", "us-info.com",
                                    "mapcarta.com", "sanantonio.com", "miami.com",
                                    "chicago.com", "houston.com", "dallas.com",
                                    "losangeles.com", "newyork.com", "phoenix.com",
                                    "tampa.com", "denver.com", "austin.com",
                                    "toronto.com", "calgary.com", "vancouver.com",
                                    "local.yahoo.com", "supermedia.com",
                                    "insiderpages.com", "cityvox.com", "kudzu.com",
                                    "talklocal.com", "service magic.com", "service-magic.com",
                                    "homestars.com", "wiseragent.com",
                                    "realtor.com", "zillow.com", "trulia.com",
                                    "remax.com", "coldwellbanker.com", "century21.com",
                                    "realestateagent.com", "movoto.com",
                                    "openstreetmap.org", "osm.org", "nominatim.org",
                                    "overpass-api.de", "geocoding.geo.census.gov"]
                    for link in links:
                        cleaned = re.sub(r'<[^>]+>', '', link).strip().split("?")[0].rstrip("/")
                        if not cleaned.startswith("http"):
                            cleaned = "https://" + cleaned
                        if not any(d in cleaned for d in skip_domains):
                            biz["website"] = cleaned
                            logger.info(f"  Found website for {name}: {cleaned[:50]}")
                            break
            except Exception:
                pass

    # Enrich with website details (phone, email, address from website)
    for biz in all_businesses:
        if biz.get("website"):
            try:
                details = _scrape_website_details(session, biz["website"])
                if details.get("real_name") and len(details["real_name"]) > 3:
                    cleaned = _clean_business_name(details["real_name"], biz["website"])
                    if cleaned and len(cleaned) > 3:
                        biz["name"] = cleaned
                if details.get("phone") and not biz.get("phone"):
                    validated = _validate_phone(details["phone"])
                    if validated:
                        biz["phone"] = validated
                if details.get("address") and not biz.get("address"):
                    biz["address"] = details["address"]
                if details.get("email") and not biz.get("email"):
                    biz["email"] = details["email"]
                if details.get("owner_name") and not biz.get("owner_name"):
                    biz["owner_name"] = details["owner_name"]
                for link_type in ["instagram", "facebook", "twitter"]:
                    if not biz.get(link_type) and details.get(link_type):
                        biz[link_type] = details[link_type]
            except Exception:
                pass

    # Filter out bad entries: directory emails, known bad domains, bad names
    bad_email_domains = [
        "birdeye.com", "loc8nearme.com", "universalsolardirect.com",
        "opendi.us", "us.mylocalservices.com", "brownbook.net",
        "boredombreaker.co", "bizapedia.com", "cylex.us.com",
        "chamberofcommerce.com", "manta.com", "zoominfo.com",
        "superpages.com", "hotfrog.com", "merchantcircle.com",
        "showmelocal.com", "citysearch.com", "dexknows.com",
        "n49.com", "kudzu.com", "tackk.com",
        "placedigger.com", "localsearch.com",
    ]
    filtered = []
    for biz in all_businesses:
        name = biz.get("name", "")
        email = biz.get("email", "")
        website = biz.get("website", "")

        # Skip businesses with emails from known directory platforms
        if email:
            email_domain = email.split("@")[-1].lower() if "@" in email else ""
            if any(d in email_domain for d in bad_email_domains):
                logger.info(f"  Filtered (directory email): {name} ({email})")
                continue

        # Skip businesses with website from directory platforms
        if website:
            if any(d in website.lower() for d in bad_email_domains):
                logger.info(f"  Filtered (directory website): {name} ({website})")
                continue

        # Skip bad names
        if not name or len(name) < 4:
            continue
        if name[0] in (",", ".", "-", "(", "["):
            continue
        name_lower = name.lower().strip()
        if name_lower in ("reviews", "review", "rating", "ratings", "comments", "feedback", "no name"):
            continue

        filtered.append(biz)

    all_businesses = filtered
    logger.info(f"After quality filter: {len(all_businesses)} businesses")

    # Sort: businesses with website first, then by name
    all_businesses.sort(key=lambda b: (0 if b.get("website") else 1, 0 if b.get("email") else 1))

    businesses = all_businesses[:limit]
    with_website = sum(1 for b in businesses if b.get("website"))
    with_email = sum(1 for b in businesses if b.get("email"))
    logger.info(f"Final: {len(businesses)} businesses ({with_website} with website, {with_email} with email)")
    return businesses


# ════════════════════════════════════════════════════════════════
# DUCKDUCKGO SEARCH
# ════════════════════════════════════════════════════════════════

def _search_ddg(session, query: str, limit: int) -> List[Dict]:
    """Search DuckDuckGo HTML version."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = session.get(url, headers=HEADERS, timeout=3)

    if resp.status_code != 200:
        return []

    html = resp.text
    businesses = []

    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)
    links = re.findall(r'class="result__url"[^>]*>\s*(.*?)\s*</a>', html, re.DOTALL)
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)

    for i in range(min(len(titles), limit)):
        name = _clean_html(titles[i]).strip() if i < len(titles) else ""
        url_raw = _clean_html(links[i]).strip() if i < len(links) else ""
        snippet = _clean_html(snippets[i]).strip() if i < len(snippets) else ""

        if not name or not url_raw:
            continue

        website = url_raw.split("?")[0].rstrip("/")
        if not website.startswith("http"):
            website = "https://" + website

        skip_domains = [
            "yelp.com", "tripadvisor.com", "facebook.com", "linkedin.com",
            "wikipedia.org", "yellowpages.com", "yellowpages.ca", "google.com",
            "bing.com", "duckduckgo.com", "instagram.com", "twitter.com",
            "bbb.org", "bbb.com", "angieslist.com", "angi.com", "thumbtack.com",
            "homeadvisor.com", "porch.com", "houzz.com", "mapquest.com",
            "foursquare.com", "cylex.us.com", "chamberofcommerce.com",
            "manta.com", "zoominfo.com", "glassdoor.com", "indeed.com",
            "clutch.co", "expertise.com", "bark.com", "tackk.com",
            "yellowpages.ae", "afroseek.com", "brownbook.net",
            "loc8nearme.com", "birdeye.com", "universalsolardirect.com",
            "placedigger.com", "localsearch.com",
            "nextdoor.com", "411.info", "local.us-info.com", "us-info.com",
            "mapcarta.com", "sanantonio.com", "miami.com", "chicago.com",
            "houston.com", "dallas.com", "losangeles.com", "newyork.com",
            "phoenix.com", "tampa.com", "denver.com", "austin.com",
            "toronto.com", "calgary.com", "vancouver.com",
            "superpages.com", "hotfrog.com", "merchantcircle.com",
            "showmelocal.com", "citysearch.com", "local.com", "dexknows.com",
            "n49.com", "boredombreaker.co", "bizapedia.com",
            "sites.google.com", "wixsite.com", "wordpress.com",
            "squarespace.com", "godaddysites.com", "weebly.com",
            "insiderpages.com", "cityvox.com", "kudzu.com",
            "talklocal.com", "service-magic.com", "homestars.com",
            "realtor.com", "zillow.com", "trulia.com", "movoto.com",
            "opendi.us", "us.mylocalservices.com", "local.yahoo.com",
            "supermedia.com", "wiseragent.com",
        ]
        if any(d in website for d in skip_domains):
            continue

        skip_title_kw = ["near me", "near ", "yellowpages", "better business", "bbb",
                         "top 10", "best 10", "compare ", "reviews of", "list of",
                         "directory", "find a ", "how to find", "cost of", "price of",
                         "vs ", "versus ", "reddit", "quora", "yelp.com", "facebook.com",
                         "youtube.com", "pinterest.com", "tiktok.com", "instagram.com",
                         "apple maps", "openstreetmap"]
        name_lower = name.lower()
        if any(kw in name_lower for kw in skip_title_kw):
            continue

        # Skip bad names: single words like "Reviews", starting with punctuation, etc.
        if name_lower.strip() in ("reviews", "review", "rating", "ratings", "comments", "feedback"):
            continue
        if name[0] in (",", ".", "-", "(", "["):
            continue
        if len(name) < 5:
            continue

        phone = ""
        phone_match = PHONE_REGEX.search(snippet)
        if phone_match:
            phone = phone_match.group(0)

        rating, review_count = _extract_rating_from_snippet(snippet)

        name = _clean_business_name(name, website)

        if len(name) < 4:
            continue

        real_name = name
        try:
            from curl_cffi import requests as cffi_requests
            _sess = cffi_requests.Session()
            details = _scrape_website_details(_sess, website)
            scraped_name = details.get("real_name", "")
            if scraped_name and len(scraped_name) > 2 and len(scraped_name) < 60:
                real_name = _clean_business_name(scraped_name, website)
            phone = _validate_phone(phone or details.get("phone", ""))
        except Exception:
            pass

        if len(real_name) > 3:
            businesses.append({
                "name": real_name,
                "rating": rating,
                "review_count": review_count,
                "website": website,
                "phone": phone or None,
                "address": "",
                "google_url": "",
                "place_id": "",
                "category": "",
                "owner_name": "",
                "instagram": "",
                "facebook": "",
                "twitter": "",
            })

    return businesses


SKIP_NAME_PATTERNS = [
    r"^HOME\s*[\|–\-]",
    r"^Contact\s+Us",
    r"^About\s+Us",
    r"^Services\s*[\|–\-]",
    r"^Our\s+Services",
    r"^About\s*[\|–\-]",
    r"^Home\s*[\|–\-]",
]


def _clean_business_name(title: str, website: str) -> str:
    name = title

    pipe_match = re.split(r'\s*[\|–]\s*', name, maxsplit=1)
    if len(pipe_match) > 1:
        name = pipe_match[0].strip()

    name = re.sub(r'\s*[\|–]\s*\w+\.(?:com|ae|sa|net|org|ca|co|us|io).*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[\|–]\s*(?:Best|Top|Cheap|Affordable|Professional|Trusted|Leading|#\d+).*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*[\|–]\s*\d{4}\b.*', '', name)
    name = re.sub(r'\s*[\(][\)]*\s*$', '', name)
    name = re.sub(r'\s*[\|–]\s*$', '', name)
    name = name.strip(" -–|()")

    CITIES = [
        "Miami", "Miami Beach", "Scottsdale", "Phoenix", "Austin", "Houston",
        "Dallas", "San Antonio", "Denver", "Tampa", "Chicago", "Atlanta",
        "Los Angeles", "Toronto", "Calgary", "Naples", "Riyadh", "Jeddah",
        "Dubai", "AbuDhabi", "Abu Dhabi", "New York", "San Diego", "Las Vegas",
    ]
    for city in CITIES:
        pattern = re.compile(rf'^{re.escape(city)}\s*', re.IGNORECASE)
        name = pattern.sub('', name)

    name = re.sub(r'\s*(?:TX|FL|AZ|CA|ON|AB|IL|GA|CO)\s*$', '', name).strip()

    for pat in SKIP_NAME_PATTERNS:
        if re.match(pat, name, re.IGNORECASE):
            name = ""
            break

    GENERIC_WORDS = {
        'medspa', 'plastic surgery', 'cosmetic dentistry', 'dental implants',
        'solar panel installer', 'solar panels', 'solar installer', 'solar energy',
        'hvac contractor', 'hvac services', 'air conditioning', 'heating and cooling',
        'roofing contractor', 'roofing services', 'personal injury lawyer',
        'personal injury attorney', 'moving company', 'movers', 'tax consultant',
        'tax accountant', 'managed it services', 'it services', 'plumber', 'plumbing',
        'electrician', 'landscaping', 'pool builder', 'estate planning',
        'dental clinic', 'dental office', 'beauty salon', 'hair salon',
        'ac repair', 'ac installation', 'furnace repair',
    }
    GENERIC_PATTERNS = [
        r'^best\b', r'^top\b', r'^cheap\b', r'^affordable\b',
        r'\bcontractor\b', r'\bservices?\b', r'\binstaller\b',
        r'\bcompany\b', r'\bconsultant\b', r'\bin\b\s+\w+$',
    ]
    name_lower = name.lower().strip()
    is_generic = name_lower in GENERIC_WORDS
    if not is_generic:
        for pat in GENERIC_PATTERNS:
            if re.search(pat, name_lower):
                is_generic = True
                break
    if is_generic or len(name.split()) < 2:
        domain_part = website.replace("https://", "").replace("http://", "").replace("www.", "").split(".")[0]
        domain_name = domain_part.replace("-", " ").replace("_", " ").title()
        if len(domain_name) > 4:
            name = domain_name

    return name.strip()


def _extract_rating_from_snippet(snippet: str) -> tuple:
    """Extract star rating and review count from DDG snippet."""
    rating = 0
    review_count = 0

    # Pattern: "4.5" or "4.5/5" or "4.5 stars"
    star_match = re.search(r'(\d+\.?\d*)\s*(?:out of 5|stars?|★|/5)', snippet, re.IGNORECASE)
    if star_match:
        try:
            r = float(star_match.group(1))
            if 1 <= r <= 5:
                rating = r
        except ValueError:
            pass

    # Pattern: "123 reviews" or "123 Google reviews"
    rev_match = re.search(r'(\d+)\s*(?:Google\s+)?reviews?', snippet, re.IGNORECASE)
    if rev_match:
        try:
            review_count = int(rev_match.group(1))
        except ValueError:
            pass

    return rating, review_count


def _search_ddg_ratings(session, query: str, limit: int) -> Dict[str, Dict]:
    """Search DDG for Google Maps ratings."""
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    resp = session.get(url, headers=HEADERS, timeout=3)

    if resp.status_code != 200:
        return {}

    html = resp.text
    snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)
    titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)

    results = {}
    for i in range(min(len(titles), limit)):
        name = _clean_html(titles[i]).strip() if i < len(titles) else ""
        snippet = _clean_html(snippets[i]).strip() if i < len(snippets) else ""

        rating, review_count = _extract_rating_from_snippet(snippet)

        if rating > 0 or review_count > 0:
            # Try to match to existing business by name similarity
            key = name.lower().strip()
            key = re.sub(r'\s*[-–|].*', '', key)
            if len(key) > 3:
                results[key] = {"rating": rating, "review_count": review_count}

    return results


def _merge_ratings(businesses: List[Dict], ratings: Dict[str, Dict]):
    """Merge DDG ratings into business list."""
    for biz in businesses:
        biz_key = biz["name"].lower().strip()
        biz_key = re.sub(r'\s*[-–|].*', '', biz_key)

        for rating_key, rating_data in ratings.items():
            if biz_key in rating_key or rating_key in biz_key:
                if not biz.get("rating") and rating_data.get("rating"):
                    biz["rating"] = rating_data["rating"]
                if not biz.get("review_count") and rating_data.get("review_count"):
                    biz["review_count"] = rating_data["review_count"]
                break


# ════════════════════════════════════════════════════════════════
# GOOGLE SEARCH
# ════════════════════════════════════════════════════════════════

def _search_google(session, query: str, limit: int) -> List[Dict]:
    """Search Google for business listings."""
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=en"
    resp = session.get(url, headers=HEADERS, timeout=3)

    if resp.status_code != 200:
        return []

    html = resp.text
    businesses = []

    h3_pattern = re.findall(r'<h3[^>]*>(.*?)</h3>', html, re.DOTALL)
    for h3 in h3_pattern[:limit]:
        name = _clean_html(h3).strip()
        if len(name) > 3 and len(name) < 100:
            businesses.append({
                "name": name,
                "rating": 0,
                "review_count": 0,
                "website": "",
                "phone": "",
                "address": "",
                "google_url": "",
                "place_id": "",
                "category": "",
                "owner_name": "",
                "instagram": "",
                "facebook": "",
                "twitter": "",
            })

    links = re.findall(r'href="(https?://[^"]*)"', html)
    skip_domains = ["google.com", "gstatic.com", "googleapis.com", "youtube.com",
                    "facebook.com", "twitter.com", "instagram.com"]
    website_links = [l for l in links if not any(d in l for d in skip_domains)]

    for i, biz in enumerate(businesses):
        if i < len(website_links):
            biz["website"] = website_links[i].split("?")[0]

    return businesses


# ════════════════════════════════════════════════════════════════
# WEBSITE DETAIL SCRAPING
# ════════════════════════════════════════════════════════════════

def _scrape_website_details(session, website_url: str) -> Dict:
    """Scrape phone, address, email, owner_name, social links from business website."""
    result = {
        "phone": "", "address": "", "email": "",
        "owner_name": "", "instagram": "", "facebook": "", "twitter": "",
        "real_name": "",
    }

    try:
        resp = session.get(website_url, headers=HEADERS, timeout=3)
        if resp.status_code != 200:
            return result

        content = resp.text
        content_lower = content.lower()

        og_site = re.search(r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)', content, re.IGNORECASE)
        if not og_site:
            og_site = re.search(r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*property=["\']og:site_name', content, re.IGNORECASE)
        if og_site:
            result["real_name"] = html.unescape(og_site.group(1).strip())

        if not result["real_name"]:
            title_tag = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
            if title_tag:
                t = html.unescape(title_tag.group(1).strip())
                t = re.sub(r'\s*[\|–]\s*(?:Home|Welcome|Offic|Servic|About|Contact).*', '', t, flags=re.IGNORECASE)
                t = re.sub(r'\s*[\|–]\s*\w+\.(com|ae|sa|net|org|ca|co).*', '', t, flags=re.IGNORECASE)
                t = t.strip(" -–|")
                if 3 < len(t) < 60:
                    result["real_name"] = t

        if not result["real_name"]:
            h1_match = re.search(r'<h1[^>]*>([^<]{3,60})</h1>', content, re.IGNORECASE)
            if h1_match:
                h1 = html.unescape(h1_match.group(1).strip())
                h1 = re.sub(r'<[^>]+>', '', h1).strip()
                if 3 < len(h1) < 60 and not any(kw in h1.lower() for kw in ["welcome", "home", "about us", "contact", "services"]):
                    result["real_name"] = h1

        phone_match = PHONE_REGEX.search(content)
        if phone_match:
            result["phone"] = _validate_phone(phone_match.group(0)) or ""

        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        if emails:
            domain = urlparse(website_url).netloc.replace("www.", "")
            domain_emails = [e for e in emails if domain in e]
            if domain_emails:
                result["email"] = domain_emails[0]
            elif emails:
                result["email"] = emails[0]

        addr_patterns = [
            r'"streetAddress"\s*:\s*"([^"]+)"',
            r'data-tooltip="([^"]*(?:street|road|avenue|suite|floor|building)[^"]*)"',
            r'(?:address|location|directions)[:\s]*([A-Z][^<\n]{10,100})',
        ]
        for pattern in addr_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                raw_addr = _clean_html(match.group(1)).strip()
                raw_addr = _validate_address(raw_addr)
                if raw_addr:
                    result["address"] = raw_addr
                    break

        owner_patterns = [
            r'(?:founder|owner|ceo|director|manager)[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'(?:founded by|owned by|managed by)[:\s]*([A-Z][a-z]+ [A-Z][a-z]+)',
            r'"name"\s*:\s*"([A-Z][a-z]+ [A-Z][a-z]+)"',
        ]
        for pattern in owner_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result["owner_name"] = match.group(1).strip()
                break

        social_patterns = {
            "instagram": r'instagram\.com/([a-zA-Z0-9_.]+)',
            "facebook": r'facebook\.com/([a-zA-Z0-9_.]+)',
            "twitter": r'twitter\.com/([a-zA-Z0-9_.]+)',
        }
        for platform, pattern in social_patterns.items():
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                result[platform] = f"https://{platform}.com/{match.group(1)}"

    except Exception:
        pass

    return result


# ════════════════════════════════════════════════════════════════
# UTILITIES
# ════════════════════════════════════════════════════════════════

def _clean_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _validate_address(addr: str) -> str:
    """Clean and validate address. Return empty string if not a real address."""
    if not addr or len(addr) < 5:
        return ""

    # Remove JSON artifacts
    addr = re.sub(r'\{[^}]*\}', '', addr)
    addr = re.sub(r'"[^"]*":\s*"[^"]*"', '', addr)
    addr = re.sub(r'"[^"]*":\s*\d+', '', addr)
    addr = re.sub(r'[{}\[\]]', '', addr)
    addr = re.sub(r'^[\s,":]+|[\s,":]+$', '', addr)

    # Remove invalid characters
    if re.search(r'[{}[\]\\]', addr):
        return ""

    # Must contain at least one number (street number) or be a known street word
    street_words = ['street', 'road', 'avenue', 'boulevard', 'drive', 'lane',
                    'way', 'court', 'place', 'suite', 'floor', 'building',
                    'st ', 'rd ', 'ave ', 'blvd', 'dr ', 'ln ']
    has_number = bool(re.search(r'\d', addr))
    has_street = any(w in addr.lower() for w in street_words)
    if not has_number and not has_street:
        return ""

    # Must be at least somewhat like an address (not just random text)
    if len(addr) < 8 or len(addr) > 200:
        return ""

    # Remove trailing commas and spaces
    addr = addr.strip(" ,.")

    return addr


def _deduplicate(businesses: List[Dict]) -> List[Dict]:
    """Deduplicate by name AND website AND phone."""
    seen_names = set()
    seen_websites = set()
    seen_phones = set()
    unique = []
    for biz in businesses:
        name = (biz.get("name") or "").lower().strip()
        website = (biz.get("website") or "").lower().strip().rstrip("/").replace("www.", "")
        phone = _validate_phone(biz.get("phone", ""))

        if name and name in seen_names:
            continue
        if website and website in seen_websites:
            continue
        if phone and phone in seen_phones:
            continue

        if name:
            seen_names.add(name)
        if website:
            seen_websites.add(website)
        if phone:
            seen_phones.add(phone)

        biz["phone"] = phone
        unique.append(biz)
    return unique


def _validate_phone(phone):
    """Validate US/Canada phone: must be exactly 10 digits. Returns formatted or None."""
    if not phone:
        return None
    digits = re.sub(r'[^0-9]', '', str(phone))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "23456789":
        return digits
    return None


def find_businesses(city: str, business_type: str, limit: int = 20) -> List[Dict]:
    """Main entry point."""
    return search_businesses(city, business_type, limit)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = find_businesses("Dubai", "dental clinic", 5)
    print(f"\nResults: {len(results)}")
    for r in results:
        print(f"  - {r['name']}")
        print(f"    Website: {r.get('website', 'N/A')}")
        print(f"    Phone: {r.get('phone', 'N/A')}")
        print(f"    Email: {r.get('email', 'N/A')}")
        print(f"    Rating: {r.get('rating', 0)}")
        print(f"    Reviews: {r.get('review_count', 0)}")
        print(f"    Owner: {r.get('owner_name', 'N/A')}")
