"""
Supported formats:
  socks5://user:pass@host:port
  http://host:port
  host:port:user:pass        (plain colon-delimited)
"""

from urllib.parse import urlparse
from typing import Optional

def parse_proxy(proxy_str: str) -> Optional[dict]:
    """Return a Pyrogram proxy dict or None if the string is empty/invalid."""
    if not proxy_str or proxy_str.strip() == "":
        return None

    s = proxy_str.strip()

    if "://" in s:
        parsed = urlparse(s)
        scheme = parsed.scheme.lower()
        if scheme not in ("socks4", "socks5", "http"):
            return None
        proxy = {
            "scheme": scheme,
            "hostname": parsed.hostname,
            "port": parsed.port,
        }
        if parsed.username:
            proxy["username"] = parsed.username
        if parsed.password:
            proxy["password"] = parsed.password
        return proxy

    parts = s.split(":")
    if len(parts) == 2:
        return {"scheme": "socks5", "hostname": parts[0], "port": int(parts[1])}
    if len(parts) == 4:
        return {
            "scheme": "socks5",
            "hostname": parts[0],
            "port": int(parts[1]),
            "username": parts[2],
            "password": parts[3],
        }

    return None