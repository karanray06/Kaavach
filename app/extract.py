import re
from typing import Dict, List, Any

# Regex patterns
URL_PATTERN = re.compile(r'https?://[^\s]+')
DOMAIN_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?:/[^\s]*)?', re.IGNORECASE)
UPI_PATTERN = re.compile(r'[\w.\-]{2,}@[a-z]{2,}', re.IGNORECASE)
PHONE_PATTERN = re.compile(r'(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}')
AMOUNT_PATTERN = re.compile(r'(?:Rs\.?|INR|\$|₹)\s*\d+(?:,\d+)*(?:\.\d+)?', re.IGNORECASE)
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', re.IGNORECASE)
CRYPTO_PATTERN = re.compile(r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|0x[a-fA-F0-9]{40}', re.IGNORECASE)

def extract_indicators(text: str) -> Dict[str, List[str]]:
    """
    Extracts IOCs (Indicators of Compromise) from text.
    Returns a dictionary of indicator types and lists of extracted values.
    """
    indicators = {
        "url": list(set(URL_PATTERN.findall(text))),
        "upi": list(set(UPI_PATTERN.findall(text))),
        "email": list(set(EMAIL_PATTERN.findall(text))),
        "crypto": list(set(CRYPTO_PATTERN.findall(text)))
    }
    
    # Filter domains from URLs or raw text
    domains = set()
    for match in DOMAIN_PATTERN.finditer(text):
        domain = match.group(1)
        # simplistic check to avoid capturing words ending in a period like "today. "
        if "." in domain and not domain.endswith("."):
            domains.add(domain.lower())
    
    # Remove email domains from standalone domains if they match exactly
    email_domains = {email.split('@')[1].lower() for email in indicators["email"]}
    indicators["domain"] = [d for d in domains if d not in email_domains]
    
    # Filter phones (at least 10 digits when stripped)
    phones = set()
    for match in PHONE_PATTERN.findall(text):
        digits_only = re.sub(r'\D', '', match)
        if len(digits_only) >= 10:
            phones.add(match.strip())
    indicators["phone"] = list(phones)
    
    # Filter amounts
    indicators["amount"] = list(set(AMOUNT_PATTERN.findall(text)))
    
    # Clean up empty lists
    return {k: v for k, v in indicators.items() if v}

def normalize_text(text: str) -> str:
    """
    Normalizes text by replacing entities with placeholders for DNA generation.
    """
    normalized = text.lower()
    # The order of replacement matters slightly
    normalized = URL_PATTERN.sub("<URL>", normalized)
    normalized = EMAIL_PATTERN.sub("<EMAIL>", normalized)
    normalized = UPI_PATTERN.sub("<UPI>", normalized)
    
    # Amounts
    normalized = AMOUNT_PATTERN.sub("<AMT>", normalized)
    
    # Phones
    for phone in PHONE_PATTERN.findall(normalized):
        digits_only = re.sub(r'\D', '', phone)
        if len(digits_only) >= 10:
            normalized = normalized.replace(phone, "<PHONE>")
            
    # Digits runs
    normalized = re.sub(r'\d+', '<N>', normalized)
    
    # Whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized
