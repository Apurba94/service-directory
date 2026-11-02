"""A directory of local services: who can help with what, where and when.

It holds organisations and services, not people seeking help. Staff use it to give a good
referral, and nothing about the person being helped is entered or stored.
"""
import math
import re
from dataclasses import dataclass, field
from datetime import datetime

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
EARTH_KM = 6371.0088


@dataclass
class Service:
    id: int
    name: str
    needs: tuple
    area: str = ""
    lat: float = None
    lon: float = None
    languages: tuple = ("bn",)
    hours: str = ""
    free: bool = True
    groups: tuple = ()           # who it serves, such as women or children. Empty means everyone
    verified: str = ""           # date the details were last checked


def distance_km(a_lat, a_lon, b_lat, b_lon):
    """Great-circle distance by the haversine formula."""
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp = p2 - p1
    dl = math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1, math.sqrt(h)))


def parse_hours(text):
    """Read 'Sun-Thu 09:00-17:00; Sat 10:00-13:00'. Returns {day number: [(open, close) in minutes]}."""
    out = {}
    if not text.strip():
        return out
    if text.strip().lower() in ("24/7", "always"):
        return {d: [(0, 1440)] for d in range(7)}
    for part in text.split(";"):
        m = re.fullmatch(r"\s*([A-Za-z]{3})(?:\s*-\s*([A-Za-z]{3}))?\s+(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})\s*", part)
        if not m:
            raise ValueError(f"cannot read hours: {part.strip()}")
        a, b = m.group(1).lower(), (m.group(2) or m.group(1)).lower()
        if a not in DAYS or b not in DAYS:
            raise ValueError(f"unknown day in: {part.strip()}")
        start = int(m.group(3)) * 60 + int(m.group(4))
        end = int(m.group(5)) * 60 + int(m.group(6))
        i = DAYS.index(a)
        while True:
            out.setdefault(i, []).append((start, end))
            if i == DAYS.index(b):
                break
            i = (i + 1) % 7
    return out


def is_open(hours, when):
    """Handles periods past midnight, such as 22:00-06:00."""
    table = parse_hours(hours)
    d, m = when.weekday(), when.hour * 60 + when.minute
    for start, end in table.get(d, ()):
        if (start <= end and start <= m < end) or (start > end and m >= start):
            return True
    for start, end in table.get((d - 1) % 7, ()):
        if start > end and m < end:
            return True
    return False


def match(services, need, lat=None, lon=None, language=None, group=None, when=None, free_only=False, area=None):
    """Rank services for a need. Hard filters remove what cannot help, and the rest are scored:
    open now, close by, right language and recently checked. Returns (score, service, km, reasons)."""
    out = []
    for s in services:
        if need not in s.needs or (free_only and not s.free):
            continue
        if group and s.groups and group not in s.groups:
            continue
        score, why = 0.0, []
        km = None
        if lat is not None and s.lat is not None:
            km = distance_km(lat, lon, s.lat, s.lon)
            score += max(0, 40 - km * 2)
            why.append(f"{km:.1f} km away")
        elif area and s.area == area:
            score += 30
            why.append("in this area")
        if language:
            if language in s.languages:
                score += 25
                why.append("speaks the language")
            else:
                score -= 10
                why.append("may need an interpreter")
        if when is not None and s.hours:
            if is_open(s.hours, when):
                score += 20
                why.append("open now")
            else:
                why.append("closed now")
        if s.free:
            score += 5
        if group and group in s.groups:
            score += 10
            why.append("focused on this group")
        out.append((score, s, km, why))
    return sorted(out, key=lambda t: (-t[0], t[1].name))


def gaps(services, needs, areas):
    """Which needs have no service in which areas. A map of the missing, for coordination meetings."""
    have = {(n, s.area) for s in services for n in s.needs}
    return [(n, a) for n in needs for a in areas if (n, a) not in have]


def single_points(services, needs):
    """Needs served by only one organisation: a closure there would leave nothing."""
    counts = {}
    for s in services:
        for n in s.needs:
            counts.setdefault(n, []).append(s.name)
    return [(n, counts[n][0]) for n in needs if len(counts.get(n, ())) == 1]


def stale(services, today, days=90):
    """Services not checked recently. Outdated referrals send people on wasted journeys."""
    out = []
    for s in services:
        if not s.verified:
            out.append((s, None))
            continue
        age = (today - datetime.strptime(s.verified, "%Y-%m-%d").date()).days
        if age > days:
            out.append((s, age))
    return out
