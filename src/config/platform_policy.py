"""
CTTC Platform-Wide Centralized Policy and Rules Engine.

Defines authoritative, configurable business rules for:
1. SLA targets, warnings, and duration standards
2. Technician domain eligibility and role gating
3. Resolution generation audience detection and safety constraints
4. Priority classification and escalation policies
5. Fallback routing and on-call escalation rules
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. SLA CONFIGURATION
# ==============================================================================

SLA_POLICY = {
    "critical": {
        "target_hours": 2.0,
        "warning_threshold_pct": 75.0,
        "description": "Critical Outage / Core Infrastructure / Emergency"
    },
    "high": {
        "target_hours": 8.0,
        "warning_threshold_pct": 75.0,
        "description": "High Priority Service Degradation / Business Impairment"
    },
    "medium": {
        "target_hours": 24.0,
        "warning_threshold_pct": 75.0,
        "description": "Standard Incident / Single Subscriber Non-Outage"
    },
    "low": {
        "target_hours": 48.0,
        "warning_threshold_pct": 75.0,
        "description": "Informational / Routine Request / Minor Glitch"
    }
}

DEFAULT_SLA_TARGET_HOURS = 24.0

def get_sla_target_hours(priority: Optional[str]) -> float:
    """Retrieve authoritative SLA target in hours for a given priority."""
    if not priority:
        return DEFAULT_SLA_TARGET_HOURS
    key = str(priority).strip().lower()
    return SLA_POLICY.get(key, {}).get("target_hours", DEFAULT_SLA_TARGET_HOURS)


# ==============================================================================
# 2. TECHNICIAN DOMAIN ELIGIBILITY & ROLE GATING
# ==============================================================================

DOMAIN_ELIGIBILITY_RULES = {
    "carrier_routing": {
        "keywords": [
            "mx960", "juniper", "400g", "evpn", "qinq", "bgp", "mpls",
            "backhaul", "core router", "pe-router", "vlan tag", "optics thermal",
            "dwdm", "carrier routing", "fiber backhaul", "olt uplink"
        ],
        "allowed_roles": [
            "OLT / Network Engineer",
            "Office / NOC Technician",
            "Network Engineer",
            "Senior Network Engineer",
            "NOC Technician",
            "Network Operations Engineer",
            "Infrastructure Engineer",
            "Core Systems Engineer"
        ],
        "disallowed_roles": [
            "Truck Roll Technician",
            "ONT Specialist",
            "L1 Support",
            "Desktop Support",
            "Broadband Support"
        ],
        "minimum_match_pct": 45,
        "fallback_queue": "TECH-ENG-01"  # Ray Flores / Network Engineering On-Call
    },
    "field_fiber_splicing": {
        "keywords": [
            "fiber cut", "splice", "otdr", "feeder fiber", "splitter",
            "bulkhead", "drop cable", "attenuation", "optical loss", "macrobend",
            "distribution cable", "fiber enclosure"
        ],
        "allowed_roles": [
            "Truck Roll Technician",
            "OLT / Network Engineer",
            "Field Technician",
            "Fiber Splicer",
            "Outside Plant (OSP) Specialist",
            "Senior Technician",
            "ONT Specialist"
        ],
        "disallowed_roles": [
            "Help Desk",
            "L1 Support"
        ],
        "minimum_match_pct": 35,
        "fallback_queue": "TECH-TR-01"  # Field Services Dispatch
    },
    "premise_ont_support": {
        "keywords": [
            "ont", "modem", "router", "cat6", "ethernet", "wifi", "lan",
            "premise", "red los", "power supply", "ups", "residential gateway"
        ],
        "allowed_roles": [
            "ONT Specialist",
            "Truck Roll Technician",
            "Office / NOC Technician",
            "Field Technician",
            "Broadband Support",
            "Senior Technician",
            "L2 Support",
            "IT Support"
        ],
        "disallowed_roles": [],
        "minimum_match_pct": 30,
        "fallback_queue": "TECH-ONT-01"
    }
}


def classify_ticket_domain(ticket_text: str) -> Optional[str]:
    """Detect domain from ticket title, description, and metadata."""
    t_lower = (ticket_text or "").lower()
    for domain, rules in DOMAIN_ELIGIBILITY_RULES.items():
        if any(kw in t_lower for kw in rules["keywords"]):
            return domain
    return None


def is_technician_domain_eligible(domain: Optional[str], tech_role: str, tech_specializations: List[str]) -> Tuple[bool, str]:
    """
    Enforce hard role and specialization boundaries.
    Prevents workload balancing from overriding core engineering qualifications.
    """
    if not domain or domain not in DOMAIN_ELIGIBILITY_RULES:
        return True, "Standard domain; no hard role restrictions applied."

    rules = DOMAIN_ELIGIBILITY_RULES[domain]
    role_clean = (tech_role or "").strip()
    specs_clean = [s.strip().lower() for s in (tech_specializations or [])]

    # Check explicit disallowance
    for disallowed in rules.get("disallowed_roles", []):
        if disallowed.lower() in role_clean.lower():
            # Check if technician possesses overriding specialization
            has_override = any(allowed.lower() in s for s in specs_clean for allowed in rules.get("allowed_roles", []))
            if not has_override:
                return False, f"Role '{role_clean}' is not qualified for domain '{domain}' (requires {', '.join(rules['allowed_roles'])})."

    # Check allowed roles / specializations
    role_matches = any(allowed.lower() in role_clean.lower() for allowed in rules.get("allowed_roles", []))
    spec_matches = any(allowed.lower() in s for s in specs_clean for allowed in rules.get("allowed_roles", []))

    if role_matches or spec_matches:
        return True, f"Qualified for domain '{domain}' by role/specialization."

    return False, f"Role '{role_clean}' lacks required domain qualifications for '{domain}'."


# ==============================================================================
# 3. RESOLUTION SAFETY & AUDIENCE ENFORCEMENT
# ==============================================================================

# Dangerous operations that must NEVER be recommended to a subscriber / end-user
UNSAFE_CUSTOMER_PATTERNS = [
    # Laser / Optical hazards
    r"\blook(?:ing)?\s+into\s+(?:the\s+)?(?:fiber|optical|connector|transceiver|laser)",
    r"\bcompressed\s+air\b.*?\b(?:ferrule|bulkhead|optical\s+port|optic)\b",
    r"\bclean\s+(?:the\s+)?ferrule\s+with\s+(?:compressed\s+air|canned\s+air)",
    r"\bclean\s+optical\s+transceiver\s+internals\b",
    r"\bsplice\b.*?\bfiber\b",
    r"\bfusion\s+splic(?:er|ing)\b",
    r"\botdr\s+trace\b",
    r"\bpower\s+meter\b.*?\bpatch\s+cord\b",
    r"\boptical\s+patch\s+cord\b",
    r"\bisopropyl\s+alcohol\b",
    # CLI / Core Router access
    r"\bshow\s+interfaces\b",
    r"\bshow\s+chassis\b",
    r"\bshow\s+bgp\b",
    r"\bshow\s+evpn\b",
    r"\bset\s+interfaces\b",
    r"\bset\s+routing-instances\b",
    r"\bconfigure\s+terminal\b",
    r"\bssh\s+(?:root|admin)@",
    r"\bsudo\s+",
    r"\bcommit\b",
    r"\bjunos\b",
    r"\bcisco\b",
    r"\bmx960\b",
    r"\bcalix\s+e7",
    # Physical infrastructure manipulation
    r"\breseat\s+(?:the\s+)?(?:olt|linecard|routing\s+engine|switch\s+fabric)\b",
    r"\breplace\s+(?:the\s+)?(?:qsfp|qsfp28|sfp|transceiver|optic)\b",
    r"\bopen\s+(?:the\s+)?(?:splice\s+closure|pedestal|handhole|vault|fiber\s+cabinet)\b"
]

COMPILED_UNSAFE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in UNSAFE_CUSTOMER_PATTERNS]

def inspect_resolution_safety(resolution_text: str, audience: str = "subscriber") -> Tuple[bool, List[str]]:
    """
    Validates generated resolution notes against safety constraints.
    Returns (is_safe, list_of_violations).
    """
    if not resolution_text or audience != "subscriber":
        return True, []

    target_text = resolution_text
    if "[Customer Notice]" in resolution_text and "[Engineering" in resolution_text:
        # Only inspect customer-facing section for subscriber safety
        parts = resolution_text.split("[Engineering")
        target_text = parts[0]

    violations = []
    for pattern in COMPILED_UNSAFE_PATTERNS:
        match = pattern.search(target_text)
        if match:
            violations.append(match.group(0))

    return (len(violations) == 0), violations


def sanitize_customer_resolution(original_resolution: str, ticket_title: str = "", category: str = "") -> str:
    """
    Repairs and transforms an unsafe or carrier-level resolution note into a safe dual-section note:
    Section 1: [Customer Notice] (Safe subscriber guidance)
    Section 2: [Engineering & Operations Protocol] (Protected internal technical procedures)
    """
    # If already formatted with sections, return as-is
    if "[Customer Notice]" in original_resolution and "[Engineering" in original_resolution:
        return original_resolution

    customer_notice = (
        "1. [Customer Notice]: This issue relates to telecommunications infrastructure / carrier routing. "
        "A certified field/network engineer has been dispatched to investigate and resolve the incident. "
        "No physical or configuration action is required or permitted by the subscriber at the premises.\n"
    )

    engineering_protocol = (
        "2. [Engineering & Operations Protocol]: "
        + original_resolution.strip()
    )

    return f"{customer_notice}\n{engineering_protocol}"


def filter_resolution_for_role(resolution_text: Optional[str], role: Optional[str]) -> Optional[str]:
    """
    Enforces resolution confidentiality and role separation at the data/API boundary.
    - Technicians and Administrators: Receive full technical instructions including internal engineering protocols.
    - Subscribers / Customers (role == 'user'): Protected internal engineering protocols, privileged Junos/Cisco CLI,
      and optical maintenance instructions are strictly redacted, returning only the customer-facing notice.
    """
    if not resolution_text:
        return resolution_text

    role_clean = (role or "user").strip().lower()
    if role_clean in ["technician", "admin"]:
        return resolution_text

    # Subscriber/Customer view: Must NEVER expose internal engineering protocols
    text = str(resolution_text).strip()

    # If it contains an explicit Engineering/Internal section, isolate only the Customer Notice
    if "[Engineering" in text or "[Internal" in text:
        parts = re.split(r"\[(?:Engineering|Internal|NOC)[^\]]*\]:?", text, flags=re.IGNORECASE)
        customer_part = parts[0].strip()
        customer_part = re.sub(r"\s*2\.\s*$", "", customer_part).strip()
        if customer_part:
            return customer_part

    # If raw text contains unsafe patterns (e.g. CLI, optics), sanitize into sections and strip engineering
    is_safe, violations = inspect_resolution_safety(text, audience="subscriber")
    if not is_safe:
        sanitized = sanitize_customer_resolution(text)
        parts = re.split(r"\[(?:Engineering|Internal|NOC)[^\]]*\]:?", sanitized, flags=re.IGNORECASE)
        customer_part = parts[0].strip()
        customer_part = re.sub(r"\s*2\.\s*$", "", customer_part).strip()
        return customer_part

    return text


# ==============================================================================
# 4. STARTUP POLICY VALIDATOR
# ==============================================================================

def validate_platform_policy() -> bool:
    """Validate platform policy at backend startup to guarantee system consistency."""
    try:
        assert "critical" in SLA_POLICY and SLA_POLICY["critical"]["target_hours"] == 2.0
        assert "high" in SLA_POLICY and SLA_POLICY["high"]["target_hours"] == 8.0
        assert "carrier_routing" in DOMAIN_ELIGIBILITY_RULES
        assert len(COMPILED_UNSAFE_PATTERNS) >= 10
        logger.info("✅ CTTC Centralized Platform Policy validated successfully.")
        return True
    except Exception as e:
        logger.critical(f"❌ Failed to validate CTTC Platform Policy: {e}")
        return False


if __name__ == "__main__":
    print(f"Policy Validator: {validate_platform_policy()}")
