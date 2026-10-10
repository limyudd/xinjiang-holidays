#!/usr/bin/env python3
"""Conservatively import the Xinjiang government's annual holiday notice.

Looks for the annual holiday notice on official notice listing pages. Fails
closed: on missing/ambiguous parsing, keeps existing official.json unchanged.
"""
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = "https://www.xinjiang.gov.cn"
LISTS = [
    BASE + "/xinjiang/tzgg/zwgk_com_list.shtml",
    BASE + "/xinjiang/tzgg/zwgk_com_list_2.shtml",
    BASE + "/xinjiang/tzgg/zwgk_com_list_3.shtml",
]
TITLES = ("节假日放假时间安排", "节假日放假和冬夏季作息时间安排", "部分节假日放假时间安排")


class Html(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.links = []
        self.href = None
        self.anchor = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.anchor = []

    def handle_data(self, data):
        self.text.append(data)
        if self.href is not None:
            self.anchor.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href:
            self.links.append(("".join(self.anchor).strip(), self.href))
            self.href = None


def fetch(url):
    req = Request(url, headers={"User-Agent": "XinjiangHolidayCalendar/1.0 (+https://github.com/limyudd/xinjiang-holidays)"})
    with urlopen(req, timeout=25) as response:
        data = response.read(1_000_000)
        charset = response.headers.get_content_charset() or "utf-8"
    return data.decode(charset, errors="replace")


def parse_day(year, fragment):
    match = re.search(r"(\d{1,2})月(\d{1,2})日", fragment)
    if not match:
        raise ValueError("No date in " + fragment[:80])
    return dt.date(year, int(match[1]), int(match[2]))


def extract(article, year, url):
    h = Html()
    h.feed(article)
    text = re.sub(r"\s+", "", "".join(h.text))
    results = {}
    for key, festival in (("rouzi", "肉孜节"), ("guerbang", "古尔邦节")):
        # Anchored to the festival section; avoids unrelated references.
        sections = re.findall(r"(?:[一二三四五六七八九十]|[（(][一二三四五六七八九十]+[）)])、?"
                              + festival + r"[:：](.{0,160})", text)
        if len(sections) != 1:
            raise ValueError(f"Expected one {festival} section, got {len(sections)}")
        section = sections[0].split("。", 2)
        statement = "。".join(section[:2])
        # Festival date is written before '是...节' in official notices.
        festival_match = re.search(r"(\d{1,2}月\d{1,2}日)[^。]{0,40}?(?:是|为)[^。]{0,32}?"
                                   + festival, statement)
        if not festival_match:
            raise ValueError("Cannot confidently parse festival date: " + festival)
        fest = parse_day(year, festival_match[1])
        holiday = re.search(r"(\d{1,2}月\d{1,2}日)[^。]{0,25}?至\s*(?:(\d{1,2})月)?"
                            r"(\d{1,2})日[^。]{0,30}?放假", statement)
        if not holiday:
            raise ValueError("Cannot confidently parse holiday range: " + festival)
        m1, d1 = map(int, re.findall(r"\d+", holiday[1])[:2])
        m2, d2 = int(holiday[2] or m1), int(holiday[3])
        start, end = dt.date(year, m1, d1), dt.date(year, m2, d2)
        if not (start <= fest <= end and 1 <= (end - start).days + 1 <= 10):
            raise ValueError("Holiday range outside bounds")
        results[key] = {"date": fest.isoformat(), "holiday_start": start.isoformat(),
                        "holiday_end": end.isoformat(), "source": url}
    return results


def main():
    data_path = ROOT / "official.json"
    obj = json.loads(data_path.read_text(encoding="utf-8"))
    existing = obj.setdefault("overrides", {})
    year = dt.date.today().year + 1
    candidates = []
    for list_url in LISTS:
        try:
            h = Html()
            h.feed(fetch(list_url))
            for text, href in h.links:
                if str(year) in text and any(title in text for title in TITLES):
                    u = urljoin(list_url, href)
                    if urlparse(u).hostname == "www.xinjiang.gov.cn" and u not in candidates:
                        candidates.append(u)
        except Exception as exc:
            print("Cannot inspect listing:", list_url, exc)
    if not candidates:
        print(f"No official annual notice found for {year}; preserving predictions")
        return
    if len(candidates) != 1:
        print("Ambiguous annual notices; require review:", candidates)
        return
    url = candidates[0]
    try:
        parsed = extract(fetch(url), year, url)
    except Exception as exc:
        print("Cannot confidently extract annual notice:", exc)
        return
    if str(year) in existing and existing[str(year)] != parsed:
        print(f"Existing official override differs for {year}; manual review required")
        return
    if str(year) not in existing:
        existing[str(year)] = parsed
        data_path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Added official holidays", year, url)
    else:
        print("Official holidays already current", year)


if __name__ == "__main__":
    main()
