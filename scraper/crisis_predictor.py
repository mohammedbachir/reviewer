"""
FindLeads — Crisis Predictor AI
Hybrid Fallback Architecture: Rule-First + ML-Second.

Layer 1: Feature Extraction (static + temporal)
Layer 2: Rule-Based Base Risk (80% weight — deterministic, explainable)
Layer 3: ML Enhancement (20% weight — Hoeffding Tree, ignored when < 500 samples)
Layer 4: Graph Risk Contagion (networkx — shared hosting propagation)
Layer 5: CVSS Scoring + Actionable Intelligence (recommendations)
Layer 6: Continuous Learning (learn from every prediction)
"""

import os
import json
import base64
import logging
import pickle
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("crisis")

COLD_START_THRESHOLD = 50  # Ignore ML until we have this many samples
RULE_WEIGHT = 0.80
ML_WEIGHT = 0.20

# ════════════════════════════════════════════════════════════════
# CVSS SEVERITY MAP — CVE severity classification
# ════════════════════════════════════════════════════════════════

CRITICAL_CVE_PATTERNS = [
    "Log4Shell", "Log4j", "CVE-2021-44228", "CVE-2021-45046",
    "Heartbleed", "CVE-2014-0160",
    "ProxyLogon", "CVE-2021-26855", "CVE-2021-26857", "CVE-2021-26858", "CVE-2021-27065",
    "ProxyShell", "CVE-2021-34473", "CVE-2021-34523", "CVE-2021-31207",
    "ProxyNotShell", "CVE-2022-41040", "CVE-2022-41082",
    "BlueKeep", "CVE-2019-0708",
    "EternalBlue", "CVE-2017-0144", "CVE-2017-0145",
    "PrintNightmare", "CVE-2021-34527", "CVE-2021-36934",
    "Dirty Pipe", "CVE-2022-0847",
    "Dirty COW", "CVE-2016-5195",
    "ShellShock", "CVE-2014-6271", "CVE-2014-6278",
    "Struts2", "CVE-2017-5638", "CVE-2018-11776",
    "Spring4Shell", "CVE-2022-22965",
    "F5 BIG-IP", "CVE-2022-1388", "CVE-2021-22986",
    "Citrix", "CVE-2019-19781",
    "Fortinet", "CVE-2018-13379", "CVE-2022-40684",
    "VMware", "CVE-2021-21972", "CVE-2022-22972",
    "Atlassian", "CVE-2022-26134",
    "Confluence", "CVE-2021-44228",
    "Apache", "CVE-2021-41773", "CVE-2021-42013",
    "OpenSSL", "CVE-2022-0778", "CVE-2014-0160",
    "WordPress", "CVE-2019-6777", "CVE-2021-24558",
    "Magento", "CVE-2022-24087",
    "Drupal", "CVE-2018-7600", "CVE-2019-6341",
    "Jenkins", "CVE-2024-23897",
    "GitLab", "CVE-2021-22214", "CVE-2023-2287",
    "RCE", "SQLi", "SQL Injection", "Remote Code Execution",
    "Privilege Escalation", "Authentication Bypass",
]

HIGH_CVE_PATTERNS = [
    "XSS", "Cross-Site Scripting", "CSRF", "SSRF",
    "Directory Traversal", "Path Traversal", "File Inclusion",
    "Information Disclosure", "Denial of Service", "DoS",
    "Buffer Overflow", "Integer Overflow", "Use After Free",
    "Memory Corruption", "Heap Overflow", "Stack Overflow",
]

MEDIUM_CVE_PATTERNS = [
    "Open Redirect", "CORS", "Clickjacking",
    "Missing Headers", "Information Leak", "Weak Cipher",
    "Deprecated Protocol", "Self-Signed Certificate",
    "Default Credentials", "Weak Password",
]

# ════════════════════════════════════════════════════════════════
# CVSS SCORING
# ════════════════════════════════════════════════════════════════

def classify_cve_severity(cve_id: str) -> Tuple[str, float]:
    """Classify a CVE string into severity tier and CVSS-like score."""
    cve_upper = cve_id.upper()

    for pattern in CRITICAL_CVE_PATTERNS:
        if pattern.upper() in cve_upper:
            return "CRITICAL", 9.5

    for pattern in HIGH_CVE_PATTERNS:
        if pattern.upper() in cve_upper:
            return "HIGH", 7.5

    for pattern in MEDIUM_CVE_PATTERNS:
        if pattern.upper() in cve_upper:
            return "MEDIUM", 5.0

    if cve_upper.startswith("CVE-"):
        year_part = cve_upper.split("-")[1] if "-" in cve_upper else ""
        if year_part.isdigit():
            year = int(year_part)
            if year >= 2023:
                return "HIGH", 7.0
            elif year >= 2021:
                return "MEDIUM", 5.5
            else:
                return "LOW", 3.0

    return "UNKNOWN", 4.0


def calculate_cvss_risk_score(vulnerabilities: List) -> Dict:
    """Calculate aggregate CVSS-based risk from a list of CVEs."""
    if not vulnerabilities:
        return {"cvss_total": 0, "cvss_max": 0, "critical_count": 0,
                "high_count": 0, "medium_count": 0, "low_count": 0,
                "severity": "NONE", "risk_multiplier": 1.0}

    critical = 0
    high = 0
    medium = 0
    low = 0
    max_score = 0

    for vuln in vulnerabilities:
        severity, score = classify_cve_severity(str(vuln))
        max_score = max(max_score, score)
        if severity == "CRITICAL":
            critical += 1
        elif severity == "HIGH":
            high += 1
        elif severity == "MEDIUM":
            medium += 1
        else:
            low += 1

    total = critical * 10 + high * 7 + medium * 4 + low * 1

    if critical > 0:
        severity = "CRITICAL"
        multiplier = 2.5
    elif high >= 2:
        severity = "HIGH"
        multiplier = 2.0
    elif high >= 1:
        severity = "ELEVATED"
        multiplier = 1.5
    elif medium >= 3:
        severity = "MEDIUM"
        multiplier = 1.3
    elif medium >= 1:
        severity = "MODERATE"
        multiplier = 1.1
    elif low > 0:
        severity = "LOW"
        multiplier = 1.0
    else:
        severity = "NONE"
        multiplier = 1.0

    return {
        "cvss_total": total,
        "cvss_max": max_score,
        "critical_count": critical,
        "high_count": high,
        "medium_count": medium,
        "low_count": low,
        "severity": severity,
        "risk_multiplier": multiplier,
    }


# ════════════════════════════════════════════════════════════════
# LAYER 1: FEATURE EXTRACTION
# ════════════════════════════════════════════════════════════════

SSL_GRADE_MAP = {"A": 0, "B": 1, "C": 2, "D": 3, "F": 4}
DANGEROUS_PORTS = {3306, 5432, 6379, 27017, 9200, 11211, 21, 23}


def _safe_int(val, default=0):
    """Safely cast to int (handles strings from Supabase)."""
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    """Safely cast to float (handles strings from Supabase)."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_list(val):
    """Parse a value that might be a JSON string, list, or None."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def extract_features(biz: Dict, snapshots: Optional[List] = None) -> Dict:
    """Extract feature vector for ML model. Combines static + temporal features."""
    features = {}

    ssl_grade = biz.get("ssl_grade", "F")
    if isinstance(ssl_grade, str):
        ssl_grade = ssl_grade.strip().upper() or "F"
    features["ssl_grade_num"] = SSL_GRADE_MAP.get(ssl_grade, 4)

    features["breach_count"] = _safe_int(biz.get("breach_count", 0))
    features["health_score"] = _safe_int(biz.get("health_score", 50))
    features["vuln_count"] = _safe_int(len(_parse_list(biz.get("vulnerabilities", []))))
    features["open_ports_count"] = _safe_int(len(_parse_list(biz.get("open_ports", []))))
    features["dangerous_ports_count"] = _safe_int(len(
        [p for p in _parse_list(biz.get("open_ports", [])) if p in DANGEROUS_PORTS]
    ))
    features["warning_count"] = _safe_int(len(_parse_list(biz.get("security_warnings", []))))
    features["rating"] = _safe_float(biz.get("rating", 0))
    features["review_count"] = _safe_int(biz.get("review_count", 0))
    features["has_email"] = 1 if biz.get("email") else 0

    tech_stack = _parse_list(biz.get("tech_stack", []))
    features["tech_count"] = _safe_int(len(tech_stack))
    features["has_outdated"] = 1 if any("Outdated" in str(t) or "Legacy" in str(t) for t in tech_stack) else 0

    vulns_raw = _parse_list(biz.get("vulnerabilities", []))
    cvss = calculate_cvss_risk_score(vulns_raw)
    features["cvss_total"] = _safe_float(cvss["cvss_total"])
    features["cvss_max"] = _safe_float(cvss["cvss_max"])
    features["critical_cves"] = _safe_int(cvss["critical_count"])
    features["high_cves"] = _safe_int(cvss["high_count"])

    sentiment = biz.get("sentiment", "neutral")
    features["sentiment_neg"] = 1 if sentiment == "negative" else 0
    features["sentiment_neutral"] = 1 if sentiment == "neutral" else 0

    features["responds_to_reviews"] = 1 if biz.get("responds_to_reviews") else 0

    firebase = biz.get("firebase") or {}
    if isinstance(firebase, str):
        try: firebase = json.loads(firebase)
        except: firebase = {}
    features["firebase_exposed"] = 1 if firebase.get("firebase_detected") else 0
    features["firebase_open"] = 1 if firebase.get("firebase_open") else 0

    api_keys = biz.get("api_keys") or {}
    if isinstance(api_keys, str):
        try: api_keys = json.loads(api_keys)
        except: api_keys = {}
    features["api_keys_leaked"] = _safe_int(api_keys.get("api_key_count", 0))

    archive = biz.get("archive") or {}
    if isinstance(archive, str):
        try: archive = json.loads(archive)
        except: archive = {}
    features["archive_sensitive"] = _safe_int(len(archive.get("archive_sensitive_files") or []))
    features["archive_admin_panels"] = _safe_int(len(archive.get("archive_admin_panels") or []))

    sherlock = biz.get("sherlock") or {}
    if isinstance(sherlock, str):
        try: sherlock = json.loads(sherlock)
        except: sherlock = {}
    features["social_profiles"] = _safe_int(sherlock.get("profile_count", 0))

    sec_headers = biz.get("security_headers", {})
    if isinstance(sec_headers, dict):
        features["security_headers_score"] = sec_headers.get("score", 0) / max(sec_headers.get("max_score", 16), 1)
    else:
        features["security_headers_score"] = 0.0

    ssl_deep = biz.get("ssl_deep", {})
    if isinstance(ssl_deep, dict):
        features["ssl_heartbleed"] = 1 if ssl_deep.get("heartbleed") else 0
        features["ssl_robot"] = 1 if ssl_deep.get("robot") else 0
        features["weak_ciphers_count"] = len(ssl_deep.get("weak_ciphers", []))
    else:
        features["ssl_heartbleed"] = 0
        features["ssl_robot"] = 0
        features["weak_ciphers_count"] = 0

    abuse = biz.get("abuseipdb", {})
    if isinstance(abuse, dict):
        features["abuse_score"] = abuse.get("abuse_score", 0) / 100.0
    else:
        features["abuse_score"] = 0.0

    features["health_trend"] = 0.0
    features["new_breaches"] = 0
    features["breach_trend"] = 0.0
    features["days_since_scan"] = 0
    features["num_scans"] = 0

    if snapshots and len(snapshots) >= 2:
        sorted_snaps = sorted(snapshots, key=lambda x: x.get("scan_date", ""))
        latest = sorted_snaps[-1]
        previous = sorted_snaps[-2]

        prev_health = previous.get("health_score") or 50
        curr_health = latest.get("health_score") or 50
        features["health_trend"] = round(curr_health - prev_health, 2)

        features["num_scans"] = len(sorted_snaps)

        try:
            latest_date = datetime.fromisoformat(latest.get("created_at", "").replace("Z", "+00:00"))
            features["days_since_scan"] = (datetime.now(timezone.utc) - latest_date).days
        except Exception:
            features["days_since_scan"] = 0

        if len(sorted_snaps) >= 3:
            older = sorted_snaps[-3]
            prev_breach = older.get("review_count", 0) or 0
            curr_breach = latest.get("review_count", 0) or 0
            features["new_breaches"] = max(0, curr_breach - prev_breach)

    return features


def get_feature_names() -> List[str]:
    """Return ordered feature names for ML model."""
    return [
        "ssl_grade_num", "breach_count", "health_score", "vuln_count",
        "open_ports_count", "dangerous_ports_count", "warning_count",
        "rating", "review_count", "has_email", "tech_count", "has_outdated",
        "cvss_total", "cvss_max", "critical_cves", "high_cves",
        "sentiment_neg", "sentiment_neutral", "responds_to_reviews",
        "firebase_exposed", "firebase_open", "api_keys_leaked",
        "archive_sensitive", "archive_admin_panels", "social_profiles",
        "security_headers_score", "ssl_heartbleed", "ssl_robot", "weak_ciphers_count",
        "abuse_score",
        "health_trend", "new_breaches", "breach_trend", "days_since_scan", "num_scans",
    ]


# ════════════════════════════════════════════════════════════════
# LAYER 2 + 4: ONLINE ML MODEL (Hoeffding Tree)
# ════════════════════════════════════════════════════════════════

class CrisisModel:
    """Hybrid Fallback: Rule-First (80%) + ML-Second (20%).

    Rule-based base risk is ALWAYS the primary signal.
    ML only contributes after cold-start threshold (500 samples) is reached.
    This prevents the Hoeffding Tree from predicting 100% for everything
    when it hasn't seen enough diverse data.
    """

    def __init__(self, model_b64: Optional[str] = None):
        self.model = None
        self.scaler = None
        self.sample_count = 0
        self._init_model(model_b64)

    def _init_model(self, model_b64: Optional[str] = None):
        try:
            from river import tree as river_tree
            from river import preprocessing as river_pre

            if model_b64:
                try:
                    raw = base64.b64decode(model_b64)
                    saved = pickle.loads(raw)
                    self.model = saved.get("model")
                    self.scaler = saved.get("scaler")
                    self.sample_count = saved.get("sample_count", 0)
                    if self.model and self.scaler:
                        logger.info(f"Loaded model from state ({self.sample_count} samples)")
                        return
                except Exception as e:
                    logger.warning(f"Failed to load model state: {e}")

            self.scaler = river_pre.StandardScaler()
            self.model = river_tree.HoeffdingTreeClassifier(
                max_depth=10,
                grace_period=20,
                delta=1e-5,
            )
            self.sample_count = 0
            logger.info("Created new Hoeffding Tree model")
        except ImportError:
            logger.warning("river library not installed — using rule-based fallback")
            self.model = None
            self.scaler = None

    def predict(self, features: Dict) -> Dict:
        """Hybrid prediction: Rule-First (80%) + ML-Second (20%).

        When sample_count < COLD_START_THRESHOLD: ML is ignored, pure rules.
        When sample_count >= COLD_START_THRESHOLD: weighted blend.
        """
        rule_result = self._rule_based_predict(features)
        rule_prob = rule_result["crisis_probability"]

        if not self.model or self.sample_count < COLD_START_THRESHOLD:
            model_type = "rule_based" if self.model else "rule_only"
            if self.model and self.sample_count < COLD_START_THRESHOLD:
                model_type = "rule_based_cold_start"
                logger.debug(f"Cold start: {self.sample_count}/{COLD_START_THRESHOLD} samples — ML ignored")
            return {
                "crisis_probability": round(rule_prob, 4),
                "risk_level": self._prob_to_level(rule_prob),
                "model_type": model_type,
                "model_trained": False,
                "rule_weight": 1.0,
                "ml_weight": 0.0,
            }

        try:
            x = {k: float(features.get(k, 0)) for k in get_feature_names()}
            x_scaled = self.scaler.transform_one(x) if self.scaler else x

            proba = self.model.predict_proba_one(x_scaled)
            ml_prob = proba.get(True, proba.get(1, 0.5))

            blended = (RULE_WEIGHT * rule_prob) + (ML_WEIGHT * ml_prob)
            blended = min(max(blended, 0.0), 1.0)

            logger.info(f"Hybrid: rules={rule_prob:.3f} × {RULE_WEIGHT} + ml={ml_prob:.3f} × {ML_WEIGHT} = {blended:.3f}")

            return {
                "crisis_probability": round(blended, 4),
                "risk_level": self._prob_to_level(blended),
                "model_type": "hybrid",
                "model_trained": True,
                "rule_weight": RULE_WEIGHT,
                "ml_weight": ML_WEIGHT,
                "rule_prob": round(rule_prob, 4),
                "ml_prob": round(ml_prob, 4),
            }
        except Exception as e:
            logger.warning(f"ML predict failed, using rules only: {e}")
            return {
                "crisis_probability": round(rule_prob, 4),
                "risk_level": self._prob_to_level(rule_prob),
                "model_type": "rule_based_fallback",
                "model_trained": False,
                "rule_weight": 1.0,
                "ml_weight": 0.0,
            }

    def learn(self, features: Dict, is_crisis: bool):
        """Online learning: teach the model from new data point."""
        if not self.model:
            return

        try:
            x = {k: float(features.get(k, 0)) for k in get_feature_names()}
            x_scaled = self.scaler.transform_one(x) if self.scaler else x
            self.model.learn_one(x_scaled, is_crisis)
            if self.scaler:
                self.scaler.learn_one(x)
            self.sample_count += 1
            if self.sample_count == COLD_START_THRESHOLD:
                logger.info(f"Cold-start threshold reached! ML now contributes {ML_WEIGHT*100:.0f}% to predictions")
        except Exception as e:
            logger.debug(f"Learn error: {e}")

    def serialize(self) -> Optional[str]:
        """Serialize model to base64 for Supabase storage."""
        if not self.model:
            return None
        try:
            data = pickle.dumps({
                "model": self.model,
                "scaler": self.scaler,
                "sample_count": self.sample_count,
            })
            return base64.b64encode(data).decode("ascii")
        except Exception as e:
            logger.warning(f"Model serialize error: {e}")
            return None

    def _rule_based_predict(self, features: Dict) -> Dict:
        """Deterministic rule-based risk scoring (explainable, always stable)."""
        score = 0.0

        ssl = features.get("ssl_grade_num", 4)
        score += [0.0, 0.05, 0.1, 0.2, 0.35][min(ssl, 4)]

        breach = features.get("breach_count", 0)
        score += min(breach * 0.2, 0.4)

        health = features.get("health_score", 50)
        if health < 30:
            score += 0.25
        elif health < 50:
            score += 0.15
        elif health < 70:
            score += 0.05

        vulns = features.get("vuln_count", 0)
        score += min(vulns * 0.05, 0.2)

        crit_cves = features.get("critical_cves", 0)
        score += min(crit_cves * 0.15, 0.3)

        dangerous = features.get("dangerous_ports_count", 0)
        score += min(dangerous * 0.08, 0.15)

        health_trend = features.get("health_trend", 0)
        if health_trend < -10:
            score += 0.15
        elif health_trend < -5:
            score += 0.08

        new_breaches = features.get("new_breaches", 0)
        if new_breaches > 0:
            score += 0.1

        firebase_open = features.get("firebase_open", 0)
        if firebase_open:
            score += 0.45

        firebase_exposed = features.get("firebase_exposed", 0)
        if firebase_exposed:
            score += 0.35

        api_keys = features.get("api_keys_leaked", 0)
        if api_keys > 50:
            score += 0.35
        elif api_keys > 20:
            score += 0.25
        elif api_keys > 10:
            score += 0.15
        elif api_keys > 0:
            score += 0.05

        archive_sensitive = features.get("archive_sensitive", 0)
        archive_admin = features.get("archive_admin_panels", 0)
        if archive_sensitive > 10 or archive_admin > 5:
            score += 0.25
        elif archive_sensitive > 0:
            score += 0.15

        social_profiles = features.get("social_profiles", 0)
        if social_profiles >= 4:
            score += 0.05

        score = min(score, 1.0)

        ssl_grade = features.get("ssl_grade_num", 4)
        health = features.get("health_score", 50)
        breach = features.get("breach_count", 0)
        vulns = features.get("vuln_count", 0)
        dangerous = features.get("dangerous_ports_count", 0)

        if ssl_grade >= 4:
            score = max(score, 0.50)
        if health < 40:
            score = max(score, 0.40)
        if breach > 0:
            score = max(score, 0.70)
        if vulns >= 3 or dangerous >= 2:
            score = max(score, 0.55)

        if firebase_open:
            score = max(score, 0.90)
        if firebase_exposed:
            score = max(score, 0.60)
        if api_keys > 50:
            score = max(score, 0.70)
        elif api_keys > 20:
            score = max(score, 0.55)
        elif api_keys > 10:
            score = max(score, 0.40)
        if archive_sensitive > 10 or archive_admin > 5:
            score = max(score, 0.50)

        return {
            "crisis_probability": round(score, 4),
            "risk_level": self._prob_to_level(score),
            "model_type": "rule_based",
            "model_trained": False,
            "rule_weight": 1.0,
            "ml_weight": 0.0,
        }

    @staticmethod
    def _prob_to_level(prob: float) -> str:
        if prob >= 0.75:
            return "CRITICAL"
        elif prob >= 0.50:
            return "HIGH"
        elif prob >= 0.25:
            return "ELEVATED"
        elif prob >= 0.10:
            return "MODERATE"
        return "LOW"


# ════════════════════════════════════════════════════════════════
# LAYER 3: GRAPH RISK CONTAGION
# ════════════════════════════════════════════════════════════════

class RiskGraph:
    """In-memory graph for risk contagion via shared infrastructure."""

    def __init__(self):
        try:
            import networkx as nx
            self.graph = nx.Graph()
            self._has_nx = True
        except ImportError:
            self.graph = {}
            self._has_nx = False
            logger.warning("networkx not installed — graph contagion disabled")

    def build_from_businesses(self, businesses: List[Dict]):
        """Build graph from business data. Links businesses sharing IPs or hosting."""
        if not self._has_nx:
            return

        for biz in businesses:
            biz_id = str(biz.get("id", ""))
            if not biz_id:
                continue
            self.graph.add_node(biz_id, **biz)

            tech_stack = biz.get("tech_stack", [])
            if isinstance(tech_stack, str):
                try:
                    tech_stack = json.loads(tech_stack)
                except Exception:
                    tech_stack = []

            for tech in tech_stack:
                if tech in ("Cloudflare", "AWS CloudFront", "Vercel", "Netlify",
                            "Firebase", "AWS S3", "DigitalOcean"):
                    shared_key = f"host:{tech}"
                    for neighbor_id in list(self.graph.nodes):
                        if neighbor_id == biz_id:
                            continue
                        neighbor_data = self.graph.nodes[neighbor_id]
                        neighbor_techs = neighbor_data.get("tech_stack", [])
                        if isinstance(neighbor_techs, str):
                            try:
                                neighbor_techs = json.loads(neighbor_techs)
                            except Exception:
                                neighbor_techs = []
                        if tech in neighbor_techs:
                            if self.graph.has_edge(neighbor_id, biz_id):
                                self.graph[neighbor_id][biz_id]["weight"] += 0.1
                            else:
                                self.graph.add_edge(neighbor_id, biz_id, weight=0.5, shared=tech)

    def propagate_risk(self, base_probs: Dict[str, float]) -> Dict[str, float]:
        """Propagate risk across connected nodes. 15% increase per critical neighbor."""
        if not self._has_nx or not self.graph:
            return base_probs

        adjusted = dict(base_probs)

        critical_nodes = {
            nid for nid, prob in base_probs.items()
            if prob >= 0.50
        }

        for crit_id in critical_nodes:
            if crit_id not in self.graph:
                continue
            for neighbor in self.graph.neighbors(crit_id):
                if neighbor in adjusted:
                    edge_data = self.graph[crit_id][neighbor]
                    weight = edge_data.get("weight", 0.5)
                    boost = 0.15 * weight
                    old = adjusted[neighbor]
                    adjusted[neighbor] = min(old + boost, 1.0)
                    if boost > 0.01:
                        logger.info(f"  Graph contagion: {crit_id} -> {neighbor} (+{boost:.3f})")

        return adjusted

    def get_neighbors(self, biz_id: str) -> List[Dict]:
        """Get connected businesses for a given node."""
        if not self._has_nx or biz_id not in self.graph:
            return []
        neighbors = []
        for neighbor in self.graph.neighbors(biz_id):
            data = self.graph.nodes[neighbor]
            edge = self.graph[biz_id][neighbor]
            neighbors.append({
                "id": neighbor,
                "name": data.get("name", ""),
                "shared_infrastructure": edge.get("shared", ""),
                "edge_weight": edge.get("weight", 0),
            })
        return neighbors


# ════════════════════════════════════════════════════════════════
# LAYER 5: ACTIONABLE INTELLIGENCE
# ════════════════════════════════════════════════════════════════

def generate_recommendations(features: Dict, prediction: Dict, cvss: Dict, neighbors: List) -> List[Dict]:
    """Generate actionable security recommendations based on analysis."""
    recs = []
    risk_level = prediction.get("risk_level", "LOW")
    prob = prediction.get("crisis_probability", 0)

    if cvss.get("critical_count", 0) > 0:
        recs.append({
            "priority": "IMMEDIATE",
            "category": "Critical CVEs",
            "message": f"{cvss['critical_count']} critical CVEs detected. Apply patches immediately or take affected services offline.",
            "impact": "Prevents active exploitation of known vulnerabilities",
        })

    if features.get("breach_count", 0) > 0:
        recs.append({
            "priority": "HIGH",
            "category": "Data Breach",
            "message": f"Domain involved in {features['breach_count']} data breach(es). Audit all credentials and rotate passwords.",
            "impact": "Limits exposure from compromised credentials",
        })

    ssl_grade = features.get("ssl_grade_num", 4)
    if ssl_grade >= 3:
        recs.append({
            "priority": "HIGH",
            "category": "SSL Certificate",
            "message": "SSL certificate has a failing grade. Renew and configure properly to prevent MITM attacks.",
            "impact": "Restores encrypted connections and customer trust",
        })

    dangerous = features.get("dangerous_ports_count", 0)
    if dangerous > 0:
        recs.append({
            "priority": "MEDIUM",
            "category": "Exposed Services",
            "message": f"{dangerous} dangerous port(s) publicly exposed. Restrict access via firewall rules.",
            "impact": "Reduces attack surface for database and cache services",
        })

    health = features.get("health_score", 50)
    if health < 40:
        recs.append({
            "priority": "MEDIUM",
            "category": "Website Health",
            "message": f"Health score is {health}/100. Comprehensive audit recommended.",
            "impact": "Improves online presence and reduces customer churn",
        })

    health_trend = features.get("health_trend", 0)
    if health_trend < -10:
        recs.append({
            "priority": "HIGH",
            "category": "Declining Health",
            "message": f"Health dropped {abs(health_trend):.0f} points since last scan. Investigate recent changes.",
            "impact": "Early detection of degrading infrastructure",
        })

    new_breaches = features.get("new_breaches", 0)
    if new_breaches > 0:
        recs.append({
            "priority": "CRITICAL",
            "category": "New Breaches",
            "message": f"{new_breaches} new breach(es) since last scan. Immediate incident response required.",
            "impact": "Stops active data exfiltration",
        })

    if neighbors:
        critical_neighbors = [n for n in neighbors if n.get("edge_weight", 0) > 0.3]
        if critical_neighbors:
            recs.append({
                "priority": "MEDIUM",
                "category": "Shared Infrastructure Risk",
                "message": f"{len(critical_neighbors)} connected business(es) share infrastructure. Compromised neighbor may affect this business.",
                "impact": "Awareness of lateral movement risk",
            })

    firebase_open = features.get("firebase_open", 0)
    if firebase_open:
        recs.append({
            "priority": "CRITICAL",
            "category": "Firebase Exposed",
            "message": "Firebase database is publicly accessible with no authentication. Customer data may be at risk of mass exfiltration.",
            "impact": "Prevents unauthorized database access and data theft",
        })
    elif features.get("firebase_exposed", 0):
        recs.append({
            "priority": "HIGH",
            "category": "Firebase Detected",
            "message": "Firebase project detected on domain. Verify authentication rules are configured to prevent unauthorized access.",
            "impact": "Ensures database access controls are properly configured",
        })

    api_keys = features.get("api_keys_leaked", 0)
    if api_keys > 50:
        recs.append({
            "priority": "CRITICAL",
            "category": "Mass API Key Exposure",
            "message": f"{api_keys} API keys/secrets exposed on website. Rotate all credentials immediately — attackers may already be harvesting them.",
            "impact": "Stops active credential theft and unauthorized service access",
        })
    elif api_keys > 20:
        recs.append({
            "priority": "HIGH",
            "category": "API Key Leakage",
            "message": f"{api_keys} API keys exposed. Rotate credentials and move secrets to environment variables.",
            "impact": "Prevents unauthorized API access and service abuse",
        })
    elif api_keys > 10:
        recs.append({
            "priority": "MEDIUM",
            "category": "API Key Exposure",
            "message": f"{api_keys} API keys found in page source. Review and remove hardcoded credentials.",
            "impact": "Reduces risk of credential-based attacks",
        })

    archive_sensitive = features.get("archive_sensitive", 0)
    archive_admin = features.get("archive_admin_panels", 0)
    if archive_sensitive > 10 or archive_admin > 5:
        recs.append({
            "priority": "HIGH",
            "category": "Archive Exposure",
            "message": f"{archive_sensitive} sensitive files and {archive_admin} admin panels found in Wayback Machine. Historical data may expose credentials or admin endpoints.",
            "impact": "Awareness of historical exposure that attackers can leverage",
        })
    elif archive_sensitive > 0:
        recs.append({
            "priority": "MEDIUM",
            "category": "Archive Artifacts",
            "message": f"{archive_sensitive} sensitive file(s) found in Wayback Machine archive. Review and remove if unnecessary.",
            "impact": "Reduces historical attack surface",
        })

    if not recs:
        recs.append({
            "priority": "INFO",
            "category": "All Clear",
            "message": "No significant security issues detected. Continue regular monitoring.",
            "impact": "Maintains current security posture",
        })

    priority_order = {"CRITICAL": 0, "IMMEDIATE": 1, "HIGH": 2, "MEDIUM": 3, "LOW": 4, "INFO": 5}
    recs.sort(key=lambda x: priority_order.get(x["priority"], 5))

    return recs


# ════════════════════════════════════════════════════════════════
# MAIN PREDICTOR
# ════════════════════════════════════════════════════════════════

def _enforce_crisis_floors(biz, prob):
    """Enforce minimum crisis probability based on raw business data.
    These are hard floors — the AI output can NEVER be lower than these."""
    ssl = biz.get("ssl_grade", "")
    if isinstance(ssl, str):
        ssl = ssl.strip().upper()
    health = _safe_int(biz.get("health_score", 50))
    breach = _safe_int(biz.get("breach_count", 0))
    vulns = _safe_int(len(_parse_list(biz.get("vulnerabilities", []))))
    dangerous = _safe_int(len([p for p in _parse_list(biz.get("open_ports", [])) if p in DANGEROUS_PORTS]))

    if ssl == "F":
        prob = max(prob, 0.50)
    if health < 40:
        prob = max(prob, 0.40)
    if breach > 0:
        prob = max(prob, 0.70)
    if vulns >= 3 or dangerous >= 2:
        prob = max(prob, 0.55)

    firebase = biz.get("firebase") or {}
    if isinstance(firebase, str):
        try: firebase = json.loads(firebase)
        except: firebase = {}
    if firebase.get("firebase_open"):
        prob = max(prob, 0.90)
    elif firebase.get("firebase_detected"):
        prob = max(prob, 0.60)

    api_keys = biz.get("api_keys") or {}
    if isinstance(api_keys, str):
        try: api_keys = json.loads(api_keys)
        except: api_keys = {}
    ak_count = _safe_int(api_keys.get("api_key_count", 0))
    if ak_count > 50:
        prob = max(prob, 0.70)
    elif ak_count > 20:
        prob = max(prob, 0.55)
    elif ak_count > 10:
        prob = max(prob, 0.40)

    archive = biz.get("archive") or {}
    if isinstance(archive, str):
        try: archive = json.loads(archive)
        except: archive = {}
    sensitive = _safe_int(len(archive.get("archive_sensitive_files") or []))
    admin_panels = _safe_int(len(archive.get("archive_admin_panels") or []))
    if sensitive > 10 or admin_panels > 5:
        prob = max(prob, 0.50)
    elif sensitive > 0:
        prob = max(prob, 0.35)

    return min(prob, 1.0)


def predict_crisis(
    biz: Dict,
    all_businesses: Optional[List[Dict]] = None,
    snapshots: Optional[List[Dict]] = None,
    model_state_b64: Optional[str] = None,
) -> Dict:
    """
    Hybrid Fallback prediction pipeline:
    1. Extract features
    2. Rule-based base risk (80% weight)
    3. ML enhancement (20% weight, ignored when < 500 samples)
    4. Graph risk contagion
    5. CVSS scoring
    6. Actionable recommendations
    7. Continuous learning
    """
    biz_id = str(biz.get("id", ""))

    features = extract_features(biz, snapshots)

    model = CrisisModel(model_state_b64)
    hybrid_result = model.predict(features)

    graph = RiskGraph()
    if all_businesses:
        graph.build_from_businesses(all_businesses)

    base_prob = {biz_id: hybrid_result["crisis_probability"]}
    if all_businesses:
        for other in all_businesses:
            other_id = str(other.get("id", ""))
            if other_id and other_id != biz_id:
                other_feats = extract_features(other)
                other_pred = model.predict(other_feats)
                base_prob[other_id] = other_pred["crisis_probability"]

    adjusted_probs = graph.propagate_risk(base_prob)
    final_prob = adjusted_probs.get(biz_id, hybrid_result["crisis_probability"])

    final_prob = _enforce_crisis_floors(biz, final_prob)

    neighbors = graph.get_neighbors(biz_id)

    cvss = calculate_cvss_risk_score(biz.get("vulnerabilities", []))

    final_risk_level = CrisisModel._prob_to_level(final_prob)

    recommendations = generate_recommendations(features, {
        "crisis_probability": final_prob,
        "risk_level": final_risk_level,
    }, cvss, neighbors)

    is_crisis = final_prob >= 0.5
    model.learn(features, is_crisis)

    return {
        "crisis_probability": round(final_prob, 4),
        "risk_level": final_risk_level,
        "model_type": hybrid_result.get("model_type", "unknown"),
        "model_trained": hybrid_result.get("model_trained", False),
        "rule_weight": hybrid_result.get("rule_weight", 1.0),
        "ml_weight": hybrid_result.get("ml_weight", 0.0),
        "sample_count": model.sample_count,
        "cvss": cvss,
        "recommendations": recommendations,
        "graph_neighbors": neighbors,
        "features": features,
        "model_state_b64": model.serialize(),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }


def predict_batch(
    businesses: List[Dict],
    model_state_b64: Optional[str] = None,
) -> List[Dict]:
    """Predict crisis for all businesses. Used by dashboard."""
    results = []
    for biz in businesses:
        result = predict_crisis(biz, all_businesses=businesses, model_state_b64=model_state_b64)
        result["business_id"] = biz.get("id")
        result["business_name"] = biz.get("name", "")
        result["city"] = biz.get("city", "")
        results.append(result)
    
    # Self-monitoring: check flagged rate
    try:
        from scraper.osint_engine import monitor_flagged_rate
        flagged_check = monitor_flagged_rate(results, batch_name="predict_batch")
        if flagged_check["status"] != "ok":
            logger.warning(f"Flagged rate alert: {flagged_check['alert']}")
    except Exception as e:
        logger.debug(f"Monitor check failed: {e}")
    
    return results
