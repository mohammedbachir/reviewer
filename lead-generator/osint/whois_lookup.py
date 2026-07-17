"""
#7 WHOIS Lookup
Retrieves domain registration info: registrar, owner, dates, nameservers, IP.
Uses python-whois + ipwhois for IP WHOIS.
"""

import socket
from typing import Dict, Optional
from datetime import datetime

try:
    import whois
except ImportError:
    whois = None

try:
    from ipwhois import IPWhois
except ImportError:
    IPWhois = None


def whois_lookup(domain: str, timeout: int = 15) -> Dict:
    """
    Perform WHOIS lookup on a domain.
    
    Returns:
        Dict with domain registration information
    """
    result = {
        "domain": domain,
        "registrar": "",
        "registrant_name": "",
        "registrant_org": "",
        "registrant_country": "",
        "created_date": "",
        "expiry_date": "",
        "updated_date": "",
        "nameservers": [],
        "status": [],
        "emails": [],
        "ip_address": "",
        "ip_whois": {},
        "days_until_expiry": None,
        "is_expired": False,
        "error": None,
    }

    if whois is None:
        result["error"] = "python-whois not installed"
        return result

    try:
        w = whois.whois(domain)

        result["registrar"] = _safe_str(w.get("registrar", ""))
        result["registrant_name"] = _safe_str(w.get("name", ""))
        result["registrant_org"] = _safe_str(w.get("org", ""))
        result["registrant_country"] = _safe_str(w.get("country", ""))

        created = w.get("creation_date")
        if isinstance(created, list):
            created = created[0] if created else None
        result["created_date"] = _format_date(created)

        expiry = w.get("expiration_date")
        if isinstance(expiry, list):
            expiry = expiry[0] if expiry else None
        result["expiry_date"] = _format_date(expiry)

        updated = w.get("updated_date")
        if isinstance(updated, list):
            updated = updated[0] if updated else None
        result["updated_date"] = _format_date(updated)

        nameservers = w.get("name_servers", [])
        if isinstance(nameservers, str):
            nameservers = [nameservers]
        result["nameservers"] = [ns.strip().lower() for ns in nameservers if ns]

        status = w.get("status", "")
        if isinstance(status, str):
            result["status"] = [status]
        elif isinstance(status, list):
            result["status"] = status
        else:
            result["status"] = []

        emails = w.get("emails", [])
        if isinstance(emails, str):
            emails = [emails]
        result["emails"] = [e for e in emails if e and "@" in str(e)]

        if expiry and isinstance(expiry, datetime):
            now = datetime.now()
            delta = expiry - now
            result["days_until_expiry"] = delta.days
            result["is_expired"] = delta.days < 0

    except Exception as e:
        result["error"] = str(e)

    try:
        ip = socket.gethostbyname(domain)
        result["ip_address"] = ip

        if IPWhois and ip:
            obj = IPWhois(ip)
            rdap = obj.lookup_rdap()
            result["ip_whois"] = {
                "asn": rdap.get("asn", ""),
                "asn_description": rdap.get("asn_description", ""),
                "asn_country": rdap.get("asn_country_code", ""),
                "network_name": rdap.get("network", {}).get("name", ""),
            }
    except Exception:
        pass

    return result


def _safe_str(value) -> str:
    """Safely convert value to string."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value).strip()


def _format_date(date) -> str:
    """Format a datetime to string."""
    if date is None:
        return ""
    if isinstance(date, datetime):
        return date.strftime("%Y-%m-%d")
    try:
        return str(date)[:10]
    except Exception:
        return ""


if __name__ == "__main__":
    test_domains = ["mmdc.ae", "godentalclinic.com", "bloombeautystudio.ae"]
    for domain in test_domains:
        print(f"\n{'='*60}")
        print(f"WHOIS: {domain}")
        print("=" * 60)
        result = whois_lookup(domain)
        print(f"  Registrar: {result['registrar']}")
        print(f"  Owner: {result['registrant_name']}")
        print(f"  Organization: {result['registrant_org']}")
        print(f"  Country: {result['registrant_country']}")
        print(f"  Created: {result['created_date']}")
        print(f"  Expires: {result['expiry_date']}")
        print(f"  Days until expiry: {result['days_until_expiry']}")
        print(f"  Nameservers: {result['nameservers']}")
        print(f"  IP: {result['ip_address']}")
        print(f"  Emails: {result['emails']}")
        if result['ip_whois']:
            print(f"  ASN: {result['ip_whois'].get('asn')}")
            print(f"  Network: {result['ip_whois'].get('network_name')}")
        if result['error']:
            print(f"  Error: {result['error']}")
