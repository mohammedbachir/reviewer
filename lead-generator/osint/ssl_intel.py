"""
#13 SSL Certificate Intelligence
Analyzes SSL certificate: issuer, validity, expiry, owner info.
Uses Python's ssl module for direct certificate inspection.
"""

import ssl
import socket
import datetime
from typing import Dict, Optional
from urllib.parse import urlparse


def ssl_intelligence(domain: str, timeout: int = 10) -> Dict:
    """
    Analyze SSL certificate of a domain.
    
    Returns:
        Dict with SSL certificate information
    """
    result = {
        "domain": domain,
        "has_ssl": False,
        "valid": False,
        "issuer": {},
        "subject": {},
        "serial_number": "",
        "not_before": "",
        "not_after": "",
        "days_until_expiry": None,
        "is_expired": False,
        "is_self_signed": False,
        "subject_alternative_names": [],
        "signature_algorithm": "",
        "error": None,
    }

    if not domain.startswith("http"):
        host = domain.replace("https://", "").replace("http://", "")
    else:
        host = urlparse(domain).hostname or domain

    host = host.split(":")[0].split("/")[0]

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert(binary_form=True)

        result["has_ssl"] = True

        unverified_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        unverified_context.check_hostname = False
        unverified_context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with unverified_context.wrap_socket(sock, server_hostname=host) as ssock:
                cert_dict = ssock.getpeercert()

        if cert_dict:
            issuer_parts = []
            for rdn in cert_dict.get("issuer", ()):
                for attr in rdn:
                    if attr[0] in ("organizationName", "commonName", "countryName"):
                        issuer_parts.append(f"{attr[0]}={attr[1]}")
            result["issuer"] = dict(
                (attr[0], attr[1])
                for rdn in cert_dict.get("issuer", ())
                for attr in rdn
            )

            subject_parts = []
            for rdn in cert_dict.get("subject", ()):
                for attr in rdn:
                    if attr[0] in ("commonName", "organizationName", "countryName"):
                        subject_parts.append(f"{attr[0]}={attr[1]}")
            result["subject"] = dict(
                (attr[0], attr[1])
                for rdn in cert_dict.get("subject", ())
                for attr in rdn
            )

            not_before = cert_dict.get("notBefore", "")
            not_after = cert_dict.get("notAfter", "")

            if not_before:
                try:
                    result["not_before"] = datetime.datetime.strptime(
                        not_before, "%b %d %H:%M:%S %Y %Z"
                    ).strftime("%Y-%m-%d")
                except Exception:
                    result["not_before"] = not_before

            if not_after:
                try:
                    expiry = datetime.datetime.strptime(
                        not_after, "%b %d %H:%M:%S %Y %Z"
                    )
                    result["not_after"] = expiry.strftime("%Y-%m-%d")

                    now = datetime.datetime.utcnow()
                    delta = expiry - now
                    result["days_until_expiry"] = delta.days
                    result["is_expired"] = delta.days < 0
                    result["valid"] = delta.days > 0
                except Exception:
                    result["not_after"] = not_after

            san_entries = cert_dict.get("subjectAltName", ())
            result["subject_alternative_names"] = [
                entry[1] for entry in san_entries if entry[0] == "DNS"
            ]

            serial = cert_dict.get("serialNumber", "")
            result["serial_number"] = serial

            issuer_cn = result["issuer"].get("commonName", "")
            subject_cn = result["subject"].get("commonName", "")
            result["is_self_signed"] = (
                issuer_cn == subject_cn
                or issuer_cn == ""
                or result["issuer"].get("organizationName", "") == result["subject"].get("organizationName", "")
            )

    except ssl.SSLCertVerificationError:
        result["has_ssl"] = True
        result["valid"] = False
        result["error"] = "SSL verification failed"
    except ConnectionRefusedError:
        result["error"] = "Port 443 refused"
    except socket.timeout:
        result["error"] = "Connection timeout"
    except socket.gaierror:
        result["error"] = "Domain not found"
    except Exception as e:
        result["error"] = str(e)

    return result


def get_ssl_grade(ssl_data: Dict) -> str:
    """Convert SSL data to a simple grade (A/B/C/D/F)."""
    if not ssl_data.get("has_ssl"):
        return "F"
    if ssl_data.get("is_expired"):
        return "F"
    if ssl_data.get("is_self_signed"):
        return "D"

    days = ssl_data.get("days_until_expiry")
    if days is not None:
        if days < 0:
            return "F"
        elif days < 30:
            return "D"
        elif days < 90:
            return "C"
        elif days < 365:
            return "B"

    issuer = ssl_data.get("issuer", {})
    org = issuer.get("organizationName", "")
    trusted_cas = ["Let's Encrypt", "DigiCert", "Comodo", "Sectigo", "GeoTrust", "Thawte"]
    if any(ca.lower() in org.lower() for ca in trusted_cas):
        return "A"

    return "B"


if __name__ == "__main__":
    test_domains = ["mmdc.ae", "godentalclinic.com", "expired.badssl.com"]
    for domain in test_domains:
        print(f"\n{'='*60}")
        print(f"SSL Intelligence: {domain}")
        print("=" * 60)
        result = ssl_intelligence(domain)
        print(f"  Has SSL: {result['has_ssl']}")
        print(f"  Valid: {result['valid']}")
        print(f"  Issuer: {result['issuer']}")
        print(f"  Not Before: {result['not_before']}")
        print(f"  Not After: {result['not_after']}")
        print(f"  Days until expiry: {result['days_until_expiry']}")
        print(f"  Self-signed: {result['is_self_signed']}")
        print(f"  Grade: {get_ssl_grade(result)}")
        if result['error']:
            print(f"  Error: {result['error']}")
