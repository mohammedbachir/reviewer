"""
#8 DNS Intelligence
Performs comprehensive DNS analysis: A, AAAA, MX, NS, TXT, CNAME, SOA records.
Uses dnspython with 8.8.8.8 as nameserver (avoids local DNS timeouts).
"""

import dns.resolver
import dns.rdatatype
from typing import Dict, List


NAMESERVERS = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]


def dns_intelligence(domain: str, timeout: int = 10) -> Dict:
    """
    Perform comprehensive DNS analysis on a domain.
    
    Returns:
        Dict with all DNS records and intelligence
    """
    result = {
        "domain": domain,
        "a_records": [],
        "aaaa_records": [],
        "mx_records": [],
        "ns_records": [],
        "txt_records": [],
        "cname_records": [],
        "soa_record": {},
        "caa_records": [],
        "has_dns": False,
        "mail_provider": "",
        "hosting_provider": "",
        "spf_valid": False,
        "dmarc_valid": False,
        "error": None,
    }

    resolver = dns.resolver.Resolver()
    resolver.nameservers = NAMESERVERS
    resolver.lifetime = timeout

    record_types = {
        "A": "a_records",
        "AAAA": "aaaa_records",
        "MX": "mx_records",
        "NS": "ns_records",
        "TXT": "txt_records",
        "CNAME": "cname_records",
        "CAA": "caa_records",
    }

    for rtype, key in record_types.items():
        try:
            answers = resolver.resolve(domain, rtype)
            for rdata in answers:
                result[key].append(str(rdata).strip('"'))
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            pass
        except dns.resolver.NoNameservers:
            pass
        except dns.exception.Timeout:
            pass
        except Exception:
            pass

    try:
        soa = resolver.resolve(domain, "SOA")
        for rdata in soa:
            result["soa_record"] = {
                "mname": str(rdata.mname),
                "rname": str(rdata.rname),
                "serial": rdata.serial,
                "refresh": rdata.refresh,
                "retry": rdata.retry,
                "expire": rdata.expire,
            }
            break
    except Exception:
        pass

    result["has_dns"] = bool(result["a_records"] or result["aaaa_records"])

    result["mail_provider"] = _detect_mail_provider(result["mx_records"])
    result["hosting_provider"] = _detect_hosting_provider(result["a_records"], result["ns_records"])

    result["spf_valid"] = _check_spf(result["txt_records"])
    result["dmarc_valid"] = _check_dmarc(domain, resolver)

    return result


def _detect_mail_provider(mx_records: List[str]) -> str:
    """Detect email provider from MX records."""
    mx_str = " ".join(mx_records).lower()
    providers = {
        "Google Workspace": ["google", "gmail", "googlemail"],
        "Microsoft 365": ["microsoft", "outlook", "microsoftonline"],
        "Zoho Mail": ["zoho"],
        "GoDaddy Email": ["secureserver", "godaddy"],
        "Cloudflare Email": ["mx.cloudflare"],
        "Namecheap Email": ["registrar-servers"],
    }
    for provider, keywords in providers.items():
        for kw in keywords:
            if kw in mx_str:
                return provider
    return "Unknown"


def _detect_hosting_provider(a_records: List[str], ns_records: List[str]) -> str:
    """Detect hosting provider from A/NS records."""
    combined = " ".join(a_records + ns_records).lower()
    providers = {
        "Cloudflare": ["cloudflare", "cf-dns"],
        "GoDaddy": ["godaddy", "secureserver", "hostgator"],
        "AWS": ["amazonaws", "aws"],
        "Google Cloud": ["google", "googledns"],
        "DigitalOcean": ["digitalocean", "digitalocean.com"],
        "Vercel": ["vercel", "vercel-dns"],
        "Netlify": ["netlify", "netlify.com"],
        "GitHub Pages": ["github.io", "github.com"],
    }
    for provider, keywords in providers.items():
        for kw in keywords:
            if kw in combined:
                return provider
    return "Unknown"


def _check_spf(txt_records: List[str]) -> bool:
    """Check if SPF record exists and is valid."""
    for record in txt_records:
        if record.lower().startswith("v=spf1"):
            return True
    return False


def _check_dmarc(domain: str, resolver) -> bool:
    """Check if DMARC record exists."""
    try:
        answers = resolver.resolve(f"_dmarc.{domain}", "TXT")
        for rdata in answers:
            if "v=DMARC1" in str(rdata):
                return True
    except Exception:
        pass
    return False


if __name__ == "__main__":
    test_domains = ["mmdc.ae", "godentalclinic.com", "bloombeautystudio.ae"]
    for domain in test_domains:
        print(f"\n{'='*60}")
        print(f"DNS Intelligence: {domain}")
        print("=" * 60)
        result = dns_intelligence(domain)
        print(f"  Has DNS: {result['has_dns']}")
        print(f"  A Records: {result['a_records']}")
        print(f"  MX Records: {result['mx_records']}")
        print(f"  NS Records: {result['ns_records']}")
        print(f"  TXT Records: {result['txt_records']}")
        print(f"  Mail Provider: {result['mail_provider']}")
        print(f"  Hosting: {result['hosting_provider']}")
        print(f"  SPF Valid: {result['spf_valid']}")
        print(f"  DMARC Valid: {result['dmarc_valid']}")
