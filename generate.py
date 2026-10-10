#!/usr/bin/env python3
"""Generate Chinese Xinjiang holiday ICS, using stdlib only."""
from __future__ import annotations
import calendar
import datetime as dt
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CALENDAR_YEARS = 15
EVENTS = [
    ("rouzi", 10, 1, "肉孜节"),
    ("guerbang", 12, 10, "古尔邦节"),
]
EPOCH = dt.date(1970, 1, 1)


def islamic_day_to_gregorian(year: int, month: int, day: int) -> dt.date:
    # Islamic civil (tabular) calendar; prediction, NOT an official crescent sighting.
    jd = (day + math.ceil(29.5 * (month - 1)) + (year - 1) * 354
          + math.floor((3 + 11 * year) / 30) + 1948439.5 - 1)
    return EPOCH + dt.timedelta(days=round(jd - 2440587.5))


def escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def folded(line: str) -> str:
    # Fold on UTF-8 byte boundaries, 75 octets maximum per RFC 5545.
    result, current = [], ""
    for char in line:
        trial = current + char
        if len(trial.encode("utf-8")) > 75:
            result.append(current)
            current = " " + char
        else:
            current = trial
    result.append(current)
    return "\r\n".join(result)


def add_event(lines: list[str], uid: str, start: dt.date, end_exclusive: dt.date,
              summary: str, description: str, stamp: str):
    record = [
        "BEGIN:VEVENT",
        "UID:" + uid + "@xinjiang-holidays",
        "DTSTAMP:" + stamp,
        "DTSTART;VALUE=DATE:" + start.strftime("%Y%m%d"),
        "DTEND;VALUE=DATE:" + end_exclusive.strftime("%Y%m%d"),
        "SUMMARY:" + escape(summary),
        "DESCRIPTION:" + escape(description),
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]
    lines.extend(folded(line) for line in record)


def main():
    current_year = dt.date.today().year
    last_year = current_year + CALENDAR_YEARS - 1
    official = json.loads((ROOT / "official.json").read_text(encoding="utf-8"))
    overrides = official.get("overrides", {})
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Xinjiang Chinese Holiday Calendar//ZH",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             "X-WR-CALNAME:新疆节假日", "X-WR-CALDESC:新疆肉孜节及古尔邦节中文日历",
             "X-WR-TIMEZONE:Asia/Shanghai"]
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Broader Hijri year range, filtered by Gregorian year below.
    for hijri_year in range(current_year - 580, last_year - 575):
        for key, month, day, title in EVENTS:
            predicted = islamic_day_to_gregorian(hijri_year, month, day)
            if not current_year <= predicted.year <= last_year:
                continue
            entry = overrides.get(str(predicted.year), {}).get(key)
            if entry:
                actual = dt.date.fromisoformat(entry["date"])
                first = dt.date.fromisoformat(entry["holiday_start"])
                last = dt.date.fromisoformat(entry["holiday_end"])
                if last < first or abs((actual - predicted).days) > 3:
                    raise ValueError(f"Invalid official override: {predicted.year}/{key}")
                source = entry.get("source", "")
                # One concise multi-day event; official status stays in event details.
                add_event(lines, f"{predicted.year}-{key}-festival", first,
                          last + dt.timedelta(days=1), title,
                          f"节日：{actual.isoformat()}\\n新疆官方放假：{first.isoformat()} 至 {last.isoformat()}\\n来源：{source}", stamp)
            else:
                add_event(lines, f"{predicted.year}-{key}-festival", predicted,
                          predicted + dt.timedelta(days=1), title,
                          "伊斯兰历推算日期，非官方放假安排；日期可能与当地公布的日期相差1至2天。", stamp)
    lines.append("END:VCALENDAR")
    out = ROOT / "docs" / "xinjiang.ics"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
    print(f"Wrote {out}, {sum(x == 'BEGIN:VEVENT' for x in lines)} events")


if __name__ == "__main__":
    main()
