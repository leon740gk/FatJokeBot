def parse_quiet_hours(value):
    """ "0-8" -> (0, 8); "23-7" wraps over midnight; empty or invalid -> None (no quiet hours)."""
    try:
        start, end = (int(part) for part in (value or "").split("-"))
    except ValueError:
        return None
    if not (0 <= start <= 23 and 0 <= end <= 24) or start == end:
        return None
    return start, end


def is_quiet(hour, quiet_hours):
    if not quiet_hours:
        return False
    start, end = quiet_hours
    return start <= hour < end if start < end else hour >= start or hour < end
