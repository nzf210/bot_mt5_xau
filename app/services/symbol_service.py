import re


KNOWN_SYMBOL_MAP = {
    "XAUUSD": ["USD"],
    "XAGUSD": ["USD"],
    "BTCUSD": ["USD"],
    "ETHUSD": ["USD"],
    "US30": ["USD"],
    "NAS100": ["USD"],
    "SPX500": ["USD"],
}


def normalize_symbol(symbol: str) -> str:
    s = symbol.upper().strip()
    s = re.sub(r"[^A-Z0-9]", "", s)

    for known in sorted(KNOWN_SYMBOL_MAP.keys(), key=len, reverse=True):
        if known in s:
            return known

    forex_match = re.match(r"([A-Z]{6})", s)
    if forex_match:
        return forex_match.group(1)

    return s


def get_symbol_currencies(symbol: str) -> list[str]:
    normalized = normalize_symbol(symbol)
    if normalized in KNOWN_SYMBOL_MAP:
        return KNOWN_SYMBOL_MAP[normalized]
    if re.fullmatch(r"[A-Z]{6}", normalized):
        return [normalized[:3], normalized[3:]]
    if normalized.endswith("USD"):
        return ["USD"]
    return ["USD"]
