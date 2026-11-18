#!/usr/bin/env python3
"""Update the energy-sector feed shown on the Market Watch pages.

Pipeline (one run every 12 hours from GitHub Actions):
  1. collect  - fetch the direct sources in config.yml (RSS / HTML link lists)
  2. triage   - Claude classifies and summarises new links, dropping irrelevant ones
  3. research - Claude searches the web for each research beat (AEMO, politics,
                tenders, events, ...) and records anything not already tracked
  4. merge    - dedupe, prune old items and write _data/energy_feed.json

Without ANTHROPIC_API_KEY the script runs in "direct-only" mode: steps 2 and 3
are skipped and direct-source items are published unsummarised, using the
category from config.yml. They are triaged once a key is available.

Usage:
  python scripts/energy_feed/update_feed.py            # normal run
  python scripts/energy_feed/update_feed.py --no-llm   # force direct-only mode
  python scripts/energy_feed/update_feed.py --only aemo,events --skip-triage
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG_PATH = HERE / "config.yml"
STATE_PATH = HERE / "state.json"
FEED_PATH = ROOT / "_data" / "energy_feed.json"


def load_dotenv(path: Path) -> None:
    """Load KEY=value lines from a local .env (gitignored) without overriding real env vars."""
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


load_dotenv(ROOT / ".env")

# Provider: a direct Anthropic key wins; otherwise use OpenRouter's Anthropic-compatible endpoint.
if os.environ.get("ANTHROPIC_API_KEY"):
    PROVIDER = "anthropic"
elif os.environ.get("OPENROUTER_API_KEY"):
    PROVIDER = "openrouter"
else:
    PROVIDER = None
# OpenRouter default: DeepSeek Flash ("~...-latest" follows DeepSeek's newest Flash release). Search and fetch
# are OpenRouter's own server tools for non-Anthropic models. Override with ENERGY_FEED_MODEL.
DEFAULT_MODEL = {"anthropic": "claude-opus-5-5", "openrouter": "~deepseek/deepseek-flash-latest"}.get(PROVIDER, "")
MODEL = os.environ.get("ENERGY_FEED_MODEL") or DEFAULT_MODEL
EFFORT = os.environ.get("ENERGY_FEED_EFFORT") or "medium"
TZ = dt.timezone(dt.timedelta(hours=8))  # Australia/Perth (no DST)

CATEGORIES = {
    "rule_change": "Rule changes: market rule change proposals, drafts and determinations (AEMC, EPWA/Coordinator of Energy), WEM/NEM procedure changes.",
    "consultation": "Consultations: open calls for submissions or feedback, reviews and exposure drafts seeking input.",
    "tender": "Tenders: RFPs, RFTs, EOIs, procurement, capacity/renewable auctions, grant and funding rounds.",
    "event": "Events: conferences, forums, webinars, information sessions, workshops.",
    "political": "Policy & politics: ministerial/government announcements, legislation, budgets, intergovernmental agreements.",
    "report": "Reports: major publications and data releases (ISP, ESOO, market reviews, statistics).",
    "news": "News: regulatory decisions, enforcement, market events and other notable industry news.",
}
JURISDICTIONS = ["WA", "NEM", "National", "NZ", "Other"]

# Topic tags. Claude picks from these keys; the keyword patterns tag items when Claude is unavailable.
TOPICS = {
    "generation": r"\bgenerat(?:or|ors|ion|ing)\b|power station|coal|wind farm|solar farm|\bthermal\b",
    "storage": r"batter(?:y|ies)|\bstorage\b|pumped hydro|\bBESS\b|long[- ]duration",
    "gas": r"\bgas\b|\bLNG\b|pipeline|GSOO|\bGSI\b",
    "renewables": r"renewable|\bsolar\b|\bwind\b|clean energy|offshore wind",
    "hydrogen": r"hydrogen|ammonia|covered gases",
    "networks": r"network|transmission|distribution|\bgrid\b|interconnector|Western Power|Transpower|lines compan|connection",
    "consumer_energy": r"rooftop|\bDER\b|distributed energy|consumer energy|plug-in|balcony solar|electric vehicle|\bEVs?\b|vehicle-to-grid|smart meter|metering",
    "reliability": r"reserve capacity|capacity mechanism|\bRCM\b|\bBRCP\b|reliability|\bESOO\b|\bPASA\b|adequacy|system security|essential system services|security of supply|dry year|firming",
    "prices": r"\bprices?\b|pricing|tariff|\bbills?\b|cost of",
    "rules": r"rule change|\brules\b|amending rules|procedure change|\bregulations?\b|national (?:electricity|gas|energy retail) law|framework|Code amendment|code change|Participation Code",
    "emissions": r"emission|climate|decarboni[sz]|net zero|\bcarbon\b|safeguard mechanism",
    "retail": r"\bretail(?:er)?s?\b|customers?|life support|hardship",
}
# Direct-only mode has no Claude triage, so drop obvious non-energy or navigation pages by title.
NOT_ENERGY_RE = re.compile(
    r"Water Corporation|water (?:licen[cs]e|services|supply)|\brail\b|Corporate Documents|Strategic Plan|"
    r"Annual Report|Careers|wildlife|biodiversity|threatened species|recycled water|timber", re.I)
SUBMISSION_RE = re.compile(
    r"consultation|submissions?|feedback|exposure draft|issues paper|draft (?:determination|report|rule)|have your say|"
    r"invitation for public|call for (?:input|comment)", re.I)
IMPORTANCE = ["high", "medium", "low"]
TRACKING_PARAMS = re.compile(r"^(utm_.*|auhash|fbclid|gclid|mc_cid|mc_eid|cid)$", re.I)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
TEXT_DATE_RE = re.compile(rf"\b(\d{{1,2}} (?:{_MONTHS}) \d{{4}})\b")
# e.g. "Media release 20 September 2026 Consultation opens on ..." -> "Consultation opens on ..."
NUMERIC_DATE_RE = re.compile(r"^(?:[A-Z]{4,}\s*)?(\d{1,2})/(\d{1,2})/(\d{4})\s+")
LEADING_LABEL_RE = re.compile(rf"^(?:[A-Z][a-z]+(?: [a-z]+)? )?\d{{1,2}} (?:{_MONTHS}) \d{{4}}\s+")
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0 Safari/537.36 isaacgumbrell.com-energy-feed",
    "Accept-Language": "en-AU,en;q=0.9",
}

log = logging.getLogger("energy_feed")
MAX_PAGE_READS = 80

# ---------------------------------------------------------------------------- browser fetch
# A few sites (AEMO, ASL) put Cloudflare in front of every page and refuse plain HTTP, but serve
# a normal page to a real browser. For hosts listed in settings.browser_hosts, pages are rendered
# in headless Chromium. It is not disguised: the user agent still names this feed, robots.txt
# allows these paths, and page loads are spaced out and capped per run. If a site still serves a
# challenge, the request fails like any other blocked request and the research beat covers it.
# Markers of a bot challenge page (Cloudflare, Imperva). Not "captcha": ordinary pages embed reCAPTCHA
# on their forms, which is not a block.
CHALLENGE_MARKERS = ("just a moment", "cf-chl", "_incapsula_resource", "verify you are human")
BROWSER_MAX_PAGES = 40     # per run
BROWSER_GAP_SECONDS = 2.0  # between page loads


class FeedSession(requests.Session):
    """requests.Session that renders listed hosts in a real browser and fetches the rest over HTTP."""

    def __init__(self, browser_hosts: list[str] | None = None):
        super().__init__()
        self.headers.update(HTTP_HEADERS)
        self.browser_hosts = tuple(h.lower() for h in (browser_hosts or []))
        self._pw = self._browser = self._page = None
        self._loads = 0
        self._last = 0.0
        self._unavailable = False

    def _wants_browser(self, url: str) -> bool:
        host = urlsplit(url).hostname or ""
        return any(host == h or host.endswith("." + h) for h in self.browser_hosts)

    def get(self, url, **kwargs):  # type: ignore[override]
        if self.browser_hosts and self._wants_browser(url):
            return self._browser_get(url)
        try:
            return super().get(url, **kwargs)
        except requests.exceptions.Timeout:
            # Some government hosts answer data-centre addresses (GitHub Actions) slowly. One slower
            # retry; a second timeout fails the source as before.
            log.info("timed out, retrying once with a longer timeout: %s", url)
            kwargs["timeout"] = max(60, kwargs.get("timeout") or 0)
            return super().get(url, **kwargs)

    def _start(self) -> bool:
        if self._page or self._unavailable:
            return bool(self._page)
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            log.warning("playwright not installed; browser hosts fall back to research beats")
            self._unavailable = True
            return False
        import shutil
        exe = os.environ.get("ENERGY_FEED_CHROMIUM") or shutil.which("chromium") or None
        try:
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True, executable_path=exe)
            ctx = self._browser.new_context(user_agent=HTTP_HEADERS["User-Agent"], locale="en-AU")
            self._page = ctx.new_page()
        except Exception as exc:
            log.warning("could not start headless browser: %s", exc)
            self._unavailable = True
            self.close()
            return False
        return True

    def _browser_get(self, url: str) -> requests.Response:
        import time
        resp = requests.Response()
        resp.url, resp.encoding = url, "utf-8"
        resp.headers["content-type"] = "text/html; charset=utf-8"
        if self._loads >= BROWSER_MAX_PAGES or not self._start():
            resp.status_code, resp._content = 503, b""
            return resp
        wait = BROWSER_GAP_SECONDS - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._loads += 1
        try:
            first = self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
            html = self._page.content()
            # Give a JS challenge time to clear, as it would for a person. It runs slower on CI
            # runners, so wait up to 30 s, then reload once (as a person would) and wait again.
            for attempt in range(2):
                for _ in range(30 if attempt == 0 else 15):
                    if not any(m in html.lower() for m in CHALLENGE_MARKERS):
                        break
                    self._page.wait_for_timeout(1000)
                    html = self._page.content()
                if attempt == 0 and any(m in html.lower() for m in CHALLENGE_MARKERS):
                    log.info("challenge still showing after 30 s, reloading once: %s", url)
                    self._page.reload(wait_until="domcontentloaded", timeout=45000)
                    html = self._page.content()
                else:
                    break
            blocked = any(m in html.lower() for m in CHALLENGE_MARKERS)
            if not blocked:
                # Listings on these sites are filled in by background requests after load.
                try:
                    self._page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                html = self._page.content()
            resp.status_code = 403 if blocked else (first.status if first else 200)
            if resp.status_code in (403, 503) and not blocked:
                resp.status_code = 200  # first response was the challenge; it cleared to the real page
            resp.url = self._page.url
            resp._content = html.encode("utf-8")
        except Exception as exc:
            log.warning("browser load failed for %s: %s", url, exc)
            resp.status_code, resp._content = 599, b""
        self._last = time.monotonic()
        return resp

    def close(self) -> None:
        for closer in (self._browser, self._pw):
            try:
                if closer is self._pw and closer:
                    closer.stop()
                elif closer:
                    closer.close()
            except Exception:
                pass
        self._pw = self._browser = self._page = None
        super().close()
BLANK_PAGE = {"description": "", "published": "", "updated": "", "deadline": "", "text": ""}
USAGE = {"input": 0, "cache_read": 0, "output": 0, "searches": 0, "fetches": 0}
COST_BY_STEP: dict[str, float] = {}  # US$ per step, as reported by OpenRouter (absent on the direct API)


# --------------------------------------------------------------------------- utils


def now() -> dt.datetime:
    return dt.datetime.now(TZ).replace(microsecond=0)


def today() -> dt.date:
    return now().date()


def normalise_url(url: str) -> str:
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def clean_url(url: str) -> str:
    """Drop tracking parameters and fragments but otherwise keep the URL as published."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not TRACKING_PARAMS.match(k)]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))


def item_id(url: str) -> str:
    return hashlib.sha1(normalise_url(url).encode()).hexdigest()[:12]


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower())[:120]


def clean_text(text: str, limit: int) -> str:
    text = " ".join(BeautifulSoup(text or "", "html.parser").get_text(" ").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def valid_date(value) -> str:
    """Return YYYY-MM-DD if value is a real date, else ''."""
    if not isinstance(value, str) or not DATE_RE.match(value.strip()):
        return ""
    try:
        return dt.date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return ""


def is_http_url(url) -> bool:
    return isinstance(url, str) and urlsplit(url).scheme in ("http", "https") and bool(urlsplit(url).netloc)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- page inspection

_MON_ABBR = r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
_ANY_DATE = rf"\d{{1,2}}\s+(?:{_MON_ABBR})\s+\d{{4}}"
PUBLISHED_TEXT_RE = re.compile(rf"(?:First published|Published|Released|Date published|Posted|Media release|Public notice)[:\s]+({_ANY_DATE})", re.I)
UPDATED_TEXT_RE = re.compile(rf"(?:Last updated|Updated|Last modified)[:\s]+({_ANY_DATE})", re.I)
DEADLINE_RE = re.compile(
    rf"(?:submissions?|feedback|comments?|responses?|registrations?|applications?|consultation|tenders?)[^.]{{0,90}}?"
    rf"(?:close|closes|closing|due|before|by|until|no later than)[^.]{{0,40}}?({_ANY_DATE})", re.I)
BOILERPLATE_RE = re.compile(
    r"^(?:Home\s*>|Fill in the form|The Australian Energy Market Commission \(AEMC\) is|Skip to|Cookies?|"
    r"This website uses|Subscribe|Share this|Print this)", re.I)


def parse_text_date(text: str) -> str:
    text = " ".join(text.split()).replace("Sept ", "Sep ")
    for fmt in ("%d %B %Y", "%d %b %Y"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def parse_iso_date(value: str) -> str:
    """ISO timestamps are converted to the Perth calendar date."""
    try:
        stamp = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return valid_date(value[:10]) if value else ""
    if stamp.tzinfo:
        stamp = stamp.astimezone(TZ)
    return stamp.date().isoformat()


def first_sentences(text: str, max_sentences: int = 2, limit: int = 320) -> str:
    text = " ".join(text.split())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    out = " ".join(parts[:max_sentences])
    return out if len(out) <= limit else out[: limit - 1].rstrip() + "…"


def keyword_topics(*texts: str) -> list[str]:
    blob = " ".join(t for t in texts if t)
    return [k for k, pat in TOPICS.items() if re.search(pat, blob, re.I)][:5]


def inspect_page(session: requests.Session, url: str) -> dict:
    """Read a source page for its description, publish/updated dates and any closing date.

    Everything here comes from the page itself; nothing is inferred. Returns empty strings when a
    value is not stated (or the site blocks scripted requests).
    """
    info = {"description": "", "published": "", "updated": "", "deadline": "", "text": ""}
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        if "html" not in resp.headers.get("content-type", ""):
            return info
    except Exception:
        return info
    soup = BeautifulSoup(resp.text, "html.parser")

    # Dates from metadata first: Open Graph / JSON-LD / Dublin Core.
    for attr, key in (("property", "article:published_time"), ("name", "dcterms.issued"),
                      ("name", "DC.date.issued"), ("name", "date"), ("itemprop", "datePublished")):
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content") and not info["published"]:
            info["published"] = parse_iso_date(tag["content"])
    if not info["published"]:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', resp.text)
        if m:
            info["published"] = parse_iso_date(m.group(1))
    if not info["published"]:
        el = soup.find(class_=re.compile(r"post-date|published-date|date-published|field--name-field-date", re.I))
        if el and (m := re.search(_ANY_DATE, el.get_text(" "), re.I)):
            info["published"] = parse_text_date(m.group(0))

    meta_desc = ""
    for attr, key in (("name", "description"), ("property", "og:description")):
        tag = soup.find("meta", attrs={attr: key})
        if tag and len((tag.get("content") or "").strip()) >= 60:
            meta_desc = tag["content"].strip()
            break

    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "form"]):
        tag.decompose()
    text = " ".join(soup.get_text(" ").split())
    info["text"] = text[:4000]

    if not info["published"] and (m := PUBLISHED_TEXT_RE.search(text)):
        info["published"] = parse_text_date(m.group(1))
    if m := UPDATED_TEXT_RE.search(text):
        info["updated"] = parse_text_date(m.group(1))
    if m := DEADLINE_RE.search(text):
        info["deadline"] = parse_text_date(m.group(1))

    if meta_desc:
        info["description"] = first_sentences(meta_desc)
    else:
        main = soup.find("main") or soup.find("article") or soup.body or soup
        for p in main.find_all("p"):
            ptext = " ".join(p.get_text(" ").split())
            if len(ptext) >= 80 and not BOILERPLATE_RE.search(ptext):
                info["description"] = first_sentences(ptext)
                break
    return info


def is_stale(item: dict, lookback_iso: str) -> bool:
    """A researched item whose deadline or event date has passed and that is not recent news."""
    t = today().isoformat()
    if item.get("category") == "event" and item.get("event_date") and item["event_date"] < t:
        return True
    closed = bool(item.get("deadline")) and item["deadline"] < t
    return closed and (not item.get("published") or item["published"] < lookback_iso)


def link_is_dead(session: requests.Session, url: str) -> bool:
    """True when a researched link plainly does not exist (404/410, or no such host).

    Guards against a model guessing a URL. Blocked or erroring pages (403, 429, 5xx, timeouts)
    are kept, because sites that refuse scripts would otherwise lose every item.

    Browser hosts (AEMO, ASL) are not checked: a full page render per link is slow, and their
    links come from their own listings or a search index rather than a guess. A check that fails
    for any reason keeps the item; it must never stop the run."""
    if isinstance(session, FeedSession) and session.browser_hosts and session._wants_browser(url):
        return False
    try:
        resp = session.get(url, timeout=20, stream=True, allow_redirects=True)
        status = resp.status_code
        if resp.raw is not None:
            resp.close()
        return status in (404, 410)
    except requests.exceptions.ConnectionError as exc:
        return "Name or service not known" in str(exc) or "NameResolutionError" in str(exc)
    except Exception:
        return False


def enrich_from_page(item: dict, info: dict) -> None:
    """Fill gaps in an item from its inspected page, never overwriting values already set."""
    if item.get("published") and item["published"] > today().isoformat():
        item["published"] = ""  # a future "publish" date is really a closing or event date
    if info["description"] and not item.get("summary"):
        item["summary"] = clean_text(info["description"], 400)
    if info["published"] and not item.get("published"):
        item["published"] = info["published"]
    if info["updated"] and not item.get("updated"):
        item["updated"] = info["updated"]
    if info["deadline"] and not item.get("deadline"):
        item["deadline"] = info["deadline"]
    if not item.get("topics"):
        item["topics"] = (keyword_topics(item.get("title", ""), item.get("summary", ""))
                          or keyword_topics(info["text"][:600]))[:3]
    if "submission_required" not in item or item.get("submission_required") is None:
        blob = f"{item.get('title', '')} {item.get('summary', '')}"
        item["submission_required"] = bool(
            item.get("category") in ("consultation", "rule_change") and (SUBMISSION_RE.search(blob) or item.get("deadline"))
            or SUBMISSION_RE.search(blob) and item.get("deadline"))
    # "Submissions open" means a written submission to a consultation or rule change, nothing else.
    if item.get("category") not in ("consultation", "rule_change"):
        item["submission_required"] = False


# --------------------------------------------------------------------------- collect


def collect_source(session: requests.Session, src: dict, lookback: dt.date) -> list[dict]:
    resp = session.get(src["url"], timeout=30)
    resp.raise_for_status()
    found: list[dict] = []

    if src["type"] == "rss":
        feed = feedparser.parse(resp.content)
        for entry in feed.entries:
            published = ""
            if entry.get("published_parsed") or entry.get("updated_parsed"):
                t = entry.get("published_parsed") or entry.get("updated_parsed")
                published = dt.date(t.tm_year, t.tm_mon, t.tm_mday).isoformat()
            elif m := re.search(r"\d{1,2} [A-Z][a-z]{2} \d{4}", entry.get("published", "")):
                # Some feeds (energy.gov.au) omit the timezone, which feedparser rejects.
                published = dt.datetime.strptime(m.group(0), "%d %b %Y").date().isoformat()
            if published and dt.date.fromisoformat(published) < lookback:
                continue
            found.append(
                {
                    "title": clean_text(entry.get("title", ""), 200),
                    "url": entry.get("link", ""),
                    "published": published,
                    "snippet": clean_text(entry.get("summary", ""), 400),
                }
            )
    else:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["nav", "header", "footer", "script", "style", "noscript"]):
            tag.decompose()
        include = re.compile(src["include"]) if src.get("include") else None
        seen = set()
        for a in soup.find_all("a", href=True):
            text = " ".join(a.get_text(" ").split())
            url = urljoin(src["url"], a["href"])
            if len(text) < 20 or not is_http_url(url) or (include and not include.search(url)):
                continue
            key = normalise_url(url)
            if key in seen or key == normalise_url(src["url"]):
                continue
            seen.add(key)
            published = ""
            if m := TEXT_DATE_RE.search(text):
                try:
                    published = dt.datetime.strptime(m.group(1), "%d %B %Y").date().isoformat()
                except ValueError:
                    pass
                text = LEADING_LABEL_RE.sub("", text) or text
            elif m := NUMERIC_DATE_RE.match(text):
                # AEMO cards: "CONSULTATION12/11/2026 Title ..." (day first, as in AU and NZ).
                try:
                    when = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                    published = when.isoformat() if when <= today() else ""
                except ValueError:
                    pass
                text = text[m.end():] or text
            # Listing pages often print dates in the row around the link: a publish date, and for
            # consultations a closing date. Labels decide which is which; a future date is never "published".
            row_deadline = ""
            row = a
            for _ in range(3):
                row = row.parent
                if row is None:
                    break
                row_text = " ".join(row.get_text(" ").split()).replace(text, " ")
                if len(row_text) > 400:
                    break
                has_date = False
                for m in re.finditer(_ANY_DATE, row_text, re.I):
                    has_date = True
                    when = parse_text_date(m.group(0))
                    label = row_text[max(0, m.start() - 40):m.start()]
                    if re.search(r"clos|due|deadline|until|submissions?", label, re.I):
                        row_deadline = row_deadline or when
                    elif when and when <= today().isoformat() and not published:
                        published = when
                if has_date:
                    break
            # Card-style links wrap a heading plus teaser text; prefer the heading as title.
            heading = a.find(["h2", "h3", "h4", "h5"])
            title = (" ".join(heading.get_text(" ").split()) if heading else text).lstrip("|–-: ")
            snippet = text.replace(title, "", 1).strip() if heading else ""
            if not published and (m := re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", snippet[:40])):
                try:  # e.g. AEMO consultation cards: "Consultation 12/11/2026 Market ..."
                    when = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                    published = when.isoformat() if when <= today() else ""
                except ValueError:
                    pass
            found.append({"title": clean_text(title, 200), "url": url, "published": published,
                          "snippet": clean_text(snippet, 400), "closing_date_on_page": row_deadline})

    for f in found:
        f.update(source=src["name"], jurisdiction=src.get("jurisdiction", "Other"),
                 category_hint=src.get("category", "news"), llm_only=bool(src.get("llm_only")))
    if src.get("match"):  # large mixed feeds (tender portals): keep only energy-looking items
        match = re.compile(src["match"], re.I)
        found = [f for f in found if match.search(f"{f['title']} {f['snippet']}")]
    return [f for f in found if f["title"] and is_http_url(f["url"])][:40]


def collect_all(cfg: dict, errors: list[str], session: requests.Session) -> list[dict]:
    lookback = today() - dt.timedelta(days=cfg["settings"]["lookback_days"])
    out: list[dict] = []
    for src in cfg["sources"]:
        try:
            items = collect_source(session, src, lookback)
            log.info("collected %3d from %s", len(items), src["url"])
            out.extend(items)
        except Exception as exc:  # one broken source must not stop the run
            msg = f"{src['name']} ({src['url']}): {exc}"
            log.warning("source failed: %s", msg)
            errors.append(msg)
    return out


# --------------------------------------------------------------------------- Claude agent

RECORD_TOOL = {
    "name": "record_items",
    "description": (
        "Save energy-sector items to the tracker. Call this with every relevant item you "
        "find; you may call it several times (up to 20 items per call). Only the items you "
        "record are published."
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["title", "url", "source", "jurisdiction", "category", "topics",
                                 "summary", "published", "deadline", "event_date", "importance",
                                 "submission_required"],
                    "properties": {
                        "title": {"type": "string", "description": "Clear, specific title as published by the source."},
                        "url": {"type": "string", "description": "Exact URL of the primary source page."},
                        "source": {"type": "string", "description": "Publishing organisation, e.g. 'AEMO', 'Energy Policy WA'."},
                        "jurisdiction": {"type": "string", "enum": JURISDICTIONS},
                        "category": {"type": "string", "enum": list(CATEGORIES)},
                        "topics": {"type": "array", "items": {"type": "string", "enum": list(TOPICS)},
                                   "description": "One to four subject tags."},
                        "submission_required": {"type": "boolean",
                                                "description": "True only for a consultation or rule change that invites written submissions or feedback. False for tenders, grants and event registrations."},
                        "summary": {"type": "string", "description": "One or two plain sentences explaining what it is and why it matters to energy professionals."},
                        "published": {"type": "string", "description": "Publication date YYYY-MM-DD, or empty string if unknown."},
                        "deadline": {"type": "string", "description": "Submission / tender / registration closing date YYYY-MM-DD, or empty string."},
                        "event_date": {"type": "string", "description": "Event start date YYYY-MM-DD (events only), or empty string."},
                        "importance": {"type": "string", "enum": IMPORTANCE},
                    },
                },
            }
        },
    },
}


def system_prompt() -> str:
    cats = "\n".join(f"- {k}: {v}" for k, v in CATEGORIES.items())
    return f"""You maintain a news tracker for Australian and New Zealand energy-sector \
professionals (market analysts, modellers, regulatory and policy staff, developers and \
consultants). Coverage priority is Western Australia (WEM, Energy Policy WA / Coordinator of \
Energy, ERA, AEMO WA, Western Power, Synergy), then the National Electricity Market and \
Australian national energy policy, and the New Zealand electricity and gas markets \
(Electricity Authority, Transpower, MBIE, Commerce Commission, Gas Industry Company).

Record items that an energy professional would want to know about: rule changes, \
consultations and submission deadlines, tenders and funding rounds, industry events, \
government energy announcements, major reports, regulatory decisions and enforcement. \
Skip items that are not about energy (water, biodiversity, waste, wildlife), routine \
corporate or HR notices, licence administrivia of minor parties, and generic marketing.

Categories:
{cats}

Topics (pick one to four): generation, storage, gas, renewables, hydrogen, networks, consumer_energy \
(rooftop solar, DER, EVs, metering), reliability (reserve capacity, adequacy, system security), prices, \
rules (market rules and regulation), emissions, retail.

Set submission_required only when a consultation or rule change invites written submissions or \
feedback. Leave it false for tenders, grants, funding rounds and event registrations: their closing \
date goes in deadline instead.

Jurisdiction: WA for Western Australian matters (including the WEM and the SWIS), NEM for \
eastern-states market matters, National for Australian Commonwealth-wide policy, NZ for New \
Zealand matters, Other otherwise.

Importance: high = changes market rules, prices, obligations or investment signals for many \
participants, or a major government decision; medium = relevant to a specific segment; \
low = minor or informational.

Rules:
- Use the exact URL of the primary source page. Never invent or guess URLs, titles or dates.
- Dates must be YYYY-MM-DD. Leave a date empty unless the source states it.
- For consultations and tenders, find the closing date when it is on the page.
- Write summaries in plain English with Australian/NZ spelling: at most two sentences and 40 words, \
saying what it is and the key facts (amounts, dates, who). State facts only: no commentary on what \
it signals or means, and no filler such as "the page has details".
- Do not record anything listed as already tracked.
- Save results with record_items. When finished, reply with one short line saying what you recorded."""


SEARCH_LOCATIONS = {
    "perth": {"type": "approximate", "city": "Perth", "region": "Western Australia",
              "country": "AU", "timezone": "Australia/Perth"},
    "nz": {"type": "approximate", "city": "Wellington", "region": "Wellington",
           "country": "NZ", "timezone": "Pacific/Auckland"},
}


def server_tools(model: str, allowed_domains: list[str], search_uses: int, fetch_uses: int,
                 search: bool, location: str = "perth") -> tuple[list[dict], list[str]]:
    """Web search/fetch tool definitions for the model, plus any beta headers they need."""
    dynamic = "haiku" not in model
    betas: list[str] = []
    tools: list[dict] = []
    if search:
        ws = {"type": "web_search_20260209" if dynamic else "web_search_20250305",
              "name": "web_search", "max_uses": search_uses,
              "user_location": SEARCH_LOCATIONS.get(location, SEARCH_LOCATIONS["perth"])}
        if allowed_domains:
            ws["allowed_domains"] = allowed_domains
        tools.append(ws)
    wf = {"type": "web_fetch_20260209" if dynamic else "web_fetch_20250910",
          "name": "web_fetch", "max_uses": fetch_uses}
    if allowed_domains:
        wf["allowed_domains"] = allowed_domains
    tools.append(wf)
    if not dynamic:
        betas.append("web-fetch-2025-09-10")
    return tools, betas


def run_agent(client, user_text: str, tools: list[dict], betas: list[str], max_iterations: int,
              label: str, search_budget: int | None = None) -> list[dict]:
    """Manual agent loop: server tools run on Anthropic's side, record_items runs here."""
    import anthropic

    recorded: list[dict] = []
    messages: list[dict] = [{"role": "user", "content": user_text}]
    extra: dict = {}
    if PROVIDER == "anthropic" and "haiku" not in MODEL:
        # Re-run on Anthropic's recommended model if a safety classifier declines.
        # (OpenRouter rejects this parameter; it does its own provider failover.)
        betas = betas + ["server-side-fallback-2026-07-01"]
        extra["fallbacks"] = "default"

    searches_used = 0
    for i in range(max_iterations):
        # A tool's max_uses applies per request, so cap the whole run here. Search fees are most
        # of the cost on cheap models.
        if search_budget is not None:
            for t in tools:
                if t.get("name") == "web_search":
                    t["max_uses"] = max(1, search_budget - searches_used)
        try:
            resp = client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=system_prompt(),
                tools=[RECORD_TOOL, *tools],
                tool_choice={"type": "auto"},
                messages=messages,
                output_config={"effort": EFFORT},
                cache_control={"type": "ephemeral"},
                betas=betas,
                **extra,
            )
        except anthropic.BadRequestError as exc:
            log.error("[%s] bad request (not retried): %s", label, exc.message)
            break
        except (anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError) as exc:
            log.error("[%s] API unavailable after SDK retries: %s", label, exc)
            break
        except anthropic.APIStatusError as exc:
            log.error("[%s] API error %s: %s", label, exc.status_code, exc.message)
            break

        u = resp.usage
        USAGE["input"] += (u.input_tokens or 0) + (getattr(u, "cache_creation_input_tokens", 0) or 0)
        USAGE["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        USAGE["output"] += u.output_tokens or 0
        if stu := getattr(u, "server_tool_use", None):
            USAGE["searches"] += getattr(stu, "web_search_requests", 0) or 0
            searches_used += getattr(stu, "web_search_requests", 0) or 0
            USAGE["fetches"] += getattr(stu, "web_fetch_requests", 0) or 0
        cost = (getattr(u, "model_extra", None) or {}).get("cost")
        if isinstance(cost, (int, float)):
            step = label.split()[0]
            COST_BY_STEP[step] = COST_BY_STEP.get(step, 0.0) + cost
        log.info("[%s] round %d: stop=%s in=%s cache_read=%s out=%s%s", label, i + 1, resp.stop_reason,
                 u.input_tokens, getattr(u, "cache_read_input_tokens", 0), u.output_tokens,
                 f" cost=${cost:.4f}" if isinstance(cost, (int, float)) else "")

        if resp.stop_reason == "refusal":
            log.warning("[%s] request declined: %s", label, getattr(resp, "stop_details", None))
            break
        messages.append({"role": "assistant", "content": [b.to_dict() for b in resp.content]})
        out_of_searches = search_budget is not None and searches_used >= search_budget
        if resp.stop_reason == "pause_turn":
            if out_of_searches:
                log.info("[%s] search budget (%d) used; stopping", label, search_budget)
                break
            continue  # server-side tool loop paused; re-send so it resumes

        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break
        results = []
        for tu in tool_uses:
            if tu.name != "record_items":
                results.append({"type": "tool_result", "tool_use_id": tu.id, "is_error": True,
                                "content": f"Unknown tool {tu.name}."})
                continue
            if resp.stop_reason == "max_tokens":
                results.append({"type": "tool_result", "tool_use_id": tu.id, "is_error": True,
                                "content": "Output was truncated. Re-send these items in smaller batches."})
                continue
            items = tu.input.get("items") if isinstance(tu.input, dict) else None
            if not isinstance(items, list):
                results.append({"type": "tool_result", "tool_use_id": tu.id, "is_error": True,
                                "content": "Expected an object with an 'items' array."})
                continue
            recorded.extend(i for i in items if isinstance(i, dict))
            results.append({"type": "tool_result", "tool_use_id": tu.id,
                            "content": f"Recorded {len(items)} item(s)."})
        messages.append({"role": "user", "content": results})
        if out_of_searches:
            log.info("[%s] search budget (%d) used; stopping", label, search_budget)
            break
    else:
        log.warning("[%s] stopped after %d rounds", label, max_iterations)

    log.info("[%s] recorded %d item(s)", label, len(recorded))
    return recorded


def known_items_text(items: list[dict], limit: int = 250) -> str:
    recent = sorted(items, key=lambda x: x.get("first_seen", ""), reverse=True)[:limit]
    return "\n".join(f"- {i['title']} | {i['url']}" for i in recent) or "(none yet)"


def triage(client, cfg: dict, candidates: list[dict]) -> tuple[list[dict], set[str]]:
    """Ask Claude which candidates are relevant. Returns (records, triaged candidate ids)."""
    s = cfg["settings"]
    records: list[dict] = []
    triaged: set[str] = set()
    size = s["triage_batch_size"]
    for start in range(0, len(candidates), size):
        batch = candidates[start:start + size]
        payload = [{k: c[k] for k in ("title", "url", "source", "jurisdiction", "category_hint",
                                      "published", "snippet", "closing_date_on_page") if c.get(k)} for c in batch]
        domains = sorted({urlsplit(c["url"]).netloc for c in batch})
        tools, betas = server_tools(MODEL, domains, 0, s["fetch_uses_per_beat"], search=False)
        user = (
            f"Today is {today().isoformat()}.\n\n"
            f"Below are {len(batch)} new links collected from official energy-sector sources. "
            "Record each one that is relevant, using its exact URL. category_hint is the "
            "source's usual category; override it when the item is clearly something else. "
            "Use web_fetch on a candidate only when you need its closing date, event date "
            "or enough detail to summarise it; skip fetching for obvious cases. Leave out "
            "links that are navigation pages, document indexes, or not about energy.\n\n"
            "<candidates>\n" + json.dumps(payload, indent=1, ensure_ascii=False) + "\n</candidates>"
        )
        got = run_agent(client, user, tools, betas, s["max_agent_iterations"],
                        f"triage {start // size + 1}")
        records.extend(got)
        triaged.update(item_id(c["url"]) for c in batch)
    return records, triaged


def research(client, cfg: dict, beat: dict, items: list[dict]) -> list[dict]:
    s = cfg["settings"]
    tools, betas = server_tools(MODEL, beat.get("allowed_domains") or [], s["search_uses_per_beat"],
                                s["fetch_uses_per_beat"], search=True,
                                location=beat.get("location", "perth"))
    user = (
        f"Today is {today().isoformat()}.\n\n"
        f"Research beat: {beat['name']}\n{beat['prompt']}\n\n"
        f"Look for items published in roughly the last {s['lookback_days']} days, plus anything "
        "still open or upcoming. Verify each item on its source page before recording it. "
        "If nothing new turns up, record nothing.\n\n"
        "<already_tracked>\n" + known_items_text(items) + "\n</already_tracked>"
    )
    return run_agent(client, user, tools, betas, s["max_agent_iterations"], beat["id"],
                     search_budget=s["search_uses_per_beat"])


# --------------------------------------------------------------------------- merge


def to_item(rec: dict, origin: str, enriched: bool, stamp: str) -> dict | None:
    url = rec.get("url", "")
    title = clean_text(rec.get("title", ""), 200)
    if not is_http_url(url) or not title:
        return None
    category = rec.get("category") if rec.get("category") in CATEGORIES else "news"
    jurisdiction = rec.get("jurisdiction") if rec.get("jurisdiction") in JURISDICTIONS else "Other"
    return {
        "id": item_id(url),
        "title": title,
        "url": clean_url(url),
        "source": clean_text(rec.get("source", ""), 80) or urlsplit(url).netloc,
        "jurisdiction": jurisdiction,
        "category": category,
        "summary": clean_text(rec.get("summary", ""), 400),
        "published": valid_date(rec.get("published")),
        "deadline": valid_date(rec.get("deadline")),
        "event_date": valid_date(rec.get("event_date")),
        "importance": rec.get("importance") if rec.get("importance") in IMPORTANCE else "medium",
        "topics": [t for t in (rec.get("topics") or []) if t in TOPICS][:4],
        "submission_required": rec.get("submission_required") if isinstance(rec.get("submission_required"), bool) else None,
        "updated": valid_date(rec.get("updated")),
        "origin": origin,
        "enriched": enriched,
        "first_seen": stamp,
    }


def similar_title(title: str, by_title: dict[str, dict]) -> dict | None:
    """Catch the same item under a longer or shorter headline, e.g. 'IPRR implementation changes'
    and 'IPRR implementation changes (ERC0458)'. The shorter title must be specific (three or more
    words, 20+ letters) so generic phrases do not match."""
    key = title_key(title)
    for other, item in by_title.items():
        short, long_, short_title = (key, other, title) if len(key) <= len(other) else (other, key, item["title"])
        if len(short) >= 20 and len(short_title.split()) >= 3 and short in long_:
            return item
    return None


def merge(items: list[dict], new: list[dict]) -> int:
    by_id = {i["id"]: i for i in items}
    by_title = {title_key(i["title"]): i for i in items}
    added = 0
    for n in new:
        old = by_id.get(n["id"]) or by_title.get(title_key(n["title"])) or similar_title(n["title"], by_title)
        if old is None:
            items.append(n)
            by_id[n["id"]] = by_title[title_key(n["title"])] = n
            added += 1
        elif n["enriched"] and not old.get("enriched"):
            old.update({k: v for k, v in n.items() if k not in ("id", "first_seen", "url")})
        elif n["enriched"]:
            # Fill gaps (e.g. a deadline found later) without overwriting existing values.
            for k in ("deadline", "event_date", "published", "summary", "topics", "updated"):
                if n[k] and not old.get(k):
                    old[k] = n[k]
    return added


def sort_date(item: dict) -> str:
    return item.get("published") or item.get("updated") or item.get("first_seen", "")[:10]


def finalise(items: list[dict], retain_days: int) -> list[dict]:
    cutoff = (today() - dt.timedelta(days=retain_days)).isoformat()
    t = today().isoformat()
    kept = []
    for i in items:
        upcoming = max(i.get("deadline") or "", i.get("event_date") or "") >= t
        if sort_date(i) >= cutoff or upcoming:
            dates = [d for d in (i.get("deadline"), i.get("event_date")) if d]
            i["due"] = min(dates) if dates else ""
            i["actionable"] = bool(i["category"] in ("consultation", "tender", "event") or i["due"])
            i["sort_date"] = sort_date(i)
            kept.append(i)
    kept.sort(key=lambda i: (i["sort_date"], i["first_seen"]), reverse=True)
    return kept


# --------------------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-llm", action="store_true", help="skip Claude; publish direct-source items only")
    ap.add_argument("--skip-triage", action="store_true", help="do not triage direct-source links")
    ap.add_argument("--skip-research", action="store_true", help="do not run research beats")
    ap.add_argument("--only", help="comma-separated research beat ids to run")
    ap.add_argument("--refresh-pages", action="store_true",
                    help="re-read source pages for existing items missing a summary, date or topics")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    cfg = yaml.safe_load(CONFIG_PATH.read_text())
    feed = load_json(FEED_PATH, {"items": []})
    state = load_json(STATE_PATH, {"ignored": {}})
    items: list[dict] = feed.get("items", [])
    errors: list[str] = []
    stamp = now().isoformat()

    use_llm = not args.no_llm and PROVIDER is not None
    if not use_llm:
        log.warning("no ANTHROPIC_API_KEY / OPENROUTER_API_KEY (or --no-llm): running in direct-only mode")
    else:
        log.info("using %s via %s (effort %s)", MODEL, PROVIDER, EFFORT)

    # One session for the whole run: plain HTTP, plus a headless browser for settings.browser_hosts.
    session = FeedSession(cfg["settings"].get("browser_hosts"))
    try:
        return run(args, cfg, feed, state, items, errors, stamp, use_llm, session)
    finally:
        session.close()


def run(args, cfg: dict, feed: dict, state: dict, items: list[dict], errors: list[str], stamp: str,
        use_llm: bool, session: FeedSession) -> int:
    # 1. collect
    candidates = collect_all(cfg, errors, session)
    known = {i["id"] for i in items}
    ignored = state["ignored"]
    fresh, seen_now = [], set()
    by_id = {i["id"]: i for i in items}
    lookback_iso = (today() - dt.timedelta(days=cfg["settings"]["lookback_days"])).isoformat()
    for c in candidates:
        cid = item_id(c["url"])
        if cid in by_id and c["published"] and not by_id[cid].get("published"):
            by_id[cid]["published"] = c["published"]  # listing date found later
        if cid in known or cid in ignored or cid in seen_now:
            continue
        if c["published"] and c["published"] < lookback_iso:
            continue  # old item on a listing page
        seen_now.add(cid)
        fresh.append(c)
    log.info("%d new direct-source candidates", len(fresh))

    # Read each new page once for its description, publish date and closing date.
    pages: dict[str, dict] = {}
    for c in fresh[:MAX_PAGE_READS]:
        info = inspect_page(session, c["url"])
        pages[item_id(c["url"])] = info
        c["published"] = c["published"] or info["published"]
        if c["published"] > today().isoformat():
            c["published"] = ""
        c["snippet"] = c["snippet"] or info["description"]
        if info["deadline"]:
            c["closing_date_on_page"] = info["deadline"]
    log.info("read %d source pages", len(pages))
    # Listings without dates (e.g. ASL) can surface old items; the page itself settles it.
    # Items that are still open (a closing date ahead) are kept whatever their age.
    stale = [c for c in fresh if c["published"] and c["published"] < lookback_iso
             and not (c.get("closing_date_on_page") or "") >= today().isoformat()]
    if stale:
        log.info("dropped %d old item(s) once their pages gave a date", len(stale))
        fresh = [c for c in fresh if c not in stale]

    new_items: list[dict] = []
    client = None
    if use_llm:
        import anthropic
        if PROVIDER == "openrouter":
            client = anthropic.Anthropic(base_url="https://openrouter.ai/api", api_key=None,
                                         auth_token=os.environ["OPENROUTER_API_KEY"], timeout=600, max_retries=3)
        else:
            client = anthropic.Anthropic(timeout=600, max_retries=3)

    # 2. triage (also re-triages recent unenriched items from direct-only runs)
    if use_llm and not args.skip_triage:
        backlog_cutoff = (today() - dt.timedelta(days=cfg["settings"]["lookback_days"])).isoformat()
        backlog = [{"title": i["title"], "url": i["url"], "source": i["source"], "jurisdiction": i["jurisdiction"],
                    "category_hint": i["category"], "published": i["published"], "snippet": i["summary"]}
                   for i in items if not i.get("enriched") and i["first_seen"][:10] >= backlog_cutoff]
        to_triage = fresh + backlog
        if to_triage:
            records, triaged = triage(client, cfg, to_triage)
            for r in records:
                if (it := to_item(r, "source", True, stamp)) and it["id"] in triaged:
                    if it["id"] in pages:
                        enrich_from_page(it, pages[it["id"]])
                    new_items.append(it)
            rejected = triaged - {n["id"] for n in new_items}
            for tid in rejected:
                ignored[tid] = today().isoformat()
            # Unenriched items (from direct-only runs) that Claude rejected leave the feed.
            items[:] = [i for i in items if i.get("enriched") or i["id"] not in rejected]
    elif not use_llm:
        items[:] = [i for i in items if i.get("enriched") or not NOT_ENERGY_RE.search(i["title"])]
        for c in fresh:
            if c["llm_only"] or NOT_ENERGY_RE.search(c["title"]):
                continue
            rec = {**c, "category": c["category_hint"], "summary": c["snippet"],
                   "deadline": c.get("closing_date_on_page", "")}
            if it := to_item(rec, "source", False, stamp):
                enrich_from_page(it, pages.get(it["id"], BLANK_PAGE))
                new_items.append(it)

    # 3. research beats
    if use_llm and not args.skip_research:
        only = set(args.only.split(",")) if args.only else None
        for beat in cfg["research"]:
            if only and beat["id"] not in only:
                continue
            for r in research(client, cfg, beat, items + new_items):
                if it := to_item(r, beat["id"], True, stamp):
                    if is_stale(it, lookback_iso):
                        log.info("[%s] dropped closed or past item: %s", beat["id"], it["title"][:80])
                        continue
                    if link_is_dead(session, it["url"]):
                        log.warning("[%s] dropped item with dead link: %s", beat["id"], it["url"])
                        continue
                    if not it["published"] and len(pages) < MAX_PAGE_READS * 2:
                        pages[it["id"]] = inspect_page(session, it["url"])
                        enrich_from_page(it, pages[it["id"]])
                    new_items.append(it)

    # 4. merge + write
    added = merge(items, new_items)
    if args.refresh_pages:
        stale = [i for i in items if not i.get("summary") or not i.get("published") or not i.get("topics")]
        for i in stale[:MAX_PAGE_READS * 2]:
            enrich_from_page(i, inspect_page(session, i["url"]))
        log.info("refreshed %d existing item(s) from their pages", min(len(stale), MAX_PAGE_READS * 2))
    for i in items:  # every item gets topics and a submission flag, from keywords if nothing better
        enrich_from_page(i, BLANK_PAGE)
    items = finalise(items, cfg["settings"]["retain_days"])
    prune_before = (today() - dt.timedelta(days=cfg["settings"]["retain_days"])).isoformat()
    state["ignored"] = {k: v for k, v in ignored.items() if v >= prune_before}

    write_json(FEED_PATH, {
        "generated_at": stamp,
        "generated_label": now().strftime("%-d %b %Y, %-I:%M %p AWST"),
        "mode": "full" if use_llm else "direct-only",
        "model": MODEL if use_llm else None,
        "sources": sorted({s["name"] for s in cfg["sources"]} | {b["name"] for b in cfg["research"]}),
        "errors": errors,
        "items": items,
    })
    write_json(STATE_PATH, state)
    log.info("added %d item(s); feed now holds %d", added, len(items))
    if use_llm:
        log.info("usage: %d input + %d cache-read + %d output tokens, %d searches, %d fetches",
                 USAGE["input"], USAGE["cache_read"], USAGE["output"], USAGE["searches"], USAGE["fetches"])
        if COST_BY_STEP:
            log.info("cost: $%.4f total (%s)", sum(COST_BY_STEP.values()),
                     ", ".join(f"{k} ${v:.4f}" for k, v in COST_BY_STEP.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
