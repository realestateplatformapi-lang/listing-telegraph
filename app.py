"""Local MVP: turn an OLX/Rieltor listing into a Telegraph article."""
import html
import ipaddress
import json
import os
import re
import socket
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from wsgiref.simple_server import make_server

import requests

ROOT = Path(__file__).parent
PORT = int(os.environ.get("PORT", "8080"))
ALLOWED_ROOT_DOMAINS = ("olx.ua", "rieltor.ua")
TELEGRAPH_API = "https://api.telegra.ph"
ACCESS_TOKEN = os.environ.get("TELEGRAPH_ACCESS_TOKEN")
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
}
LISTING_CACHE = {}
CACHE_TTL_SECONDS = 60 * 60 * 6


class ListingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta, self.json_ld, self._script = {}, [], False
        self._script_text = []
        self.title, self._in_title = "", False
        self._text_tag, self._text_parts = None, []
        self.text_blocks, self.images = [], []
        self._description_depth, self._description_parts = 0, []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = attrs.get("property") or attrs.get("name")
            value = attrs.get("content")
            if key and value:
                self.meta.setdefault(key.lower(), []).append(value)
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._script, self._script_text = True, []
        if tag == "title":
            self._in_title = True
        if tag in {"h1", "h2", "p", "li"}:
            self._text_tag, self._text_parts = tag, []
        if tag == "img":
            for key in ("src", "data-src", "data-lazy-src", "data-original"):
                if attrs.get(key):
                    self.images.append(attrs[key])
                    break
        classes = set(attrs.get("class", "").split())
        if tag == "div" and "offer-view-section-text" in classes:
            self._description_depth, self._description_parts = 1, []
        elif self._description_depth:
            self._description_depth += 1

    def handle_endtag(self, tag):
        if tag == "script" and self._script:
            self._script = False
            try:
                self.json_ld.append(json.loads("".join(self._script_text)))
            except json.JSONDecodeError:
                pass
        if tag == "title":
            self._in_title = False
        if tag == self._text_tag:
            text = " ".join(self._text_parts).strip()
            if text and len(text) > 15:
                self.text_blocks.append(text)
            self._text_tag, self._text_parts = None, []
        if self._description_depth:
            self._description_depth -= 1
            if self._description_depth == 0:
                text = " ".join(self._description_parts).strip()
                if text:
                    self.text_blocks.insert(0, text)

    def handle_data(self, data):
        if self._script:
            self._script_text.append(data)
        if self._in_title:
            self.title += data
        if self._text_tag:
            self._text_parts.append(data.strip())
        if self._description_depth:
            self._description_parts.append(data.strip())


def reject_unsafe_url(raw):
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    # Rieltor agency pages use subdomains, e.g. agency.rieltor.ua.
    valid_host = any(host == domain or host.endswith("." + domain) for domain in ALLOWED_ROOT_DOMAINS)
    if parsed.scheme != "https" or not valid_host:
        raise ValueError("Підтримуються лише HTTPS-посилання на OLX.ua та Rieltor.ua.")
    # Prevent a DNS-rebinding request from reaching a private host.
    for result in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM):
        ip = ipaddress.ip_address(result[4][0])
        if not ip.is_global:
            raise ValueError("Небезпечна адреса сайту.")


def first(data, *keys):
    for key in keys:
        values = data.get(key.lower(), [])
        if values:
            return values[0]
    return ""


def flatten_jsonld(value):
    if isinstance(value, list):
        for item in value:
            yield from flatten_jsonld(item)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from flatten_jsonld(value["@graph"])


def extract_listing(source_url):
    reject_unsafe_url(source_url)
    cache_key = source_url.rstrip("/")
    cached = LISTING_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    response = None
    # Respect the site's rate limit rather than immediately issuing another request.
    for attempt in range(2):
        response = session.get(source_url, timeout=20)
        if response.status_code != 429:
            break
        try:
            delay = min(int(response.headers.get("Retry-After", "3")), 10)
        except ValueError:
            delay = 3
        if attempt == 0:
            # A normal browser arrives with Rieltor's first-party cookies. Refresh
            # them once before retrying, while still respecting Retry-After.
            try:
                session.get("https://rieltor.ua/", timeout=15)
            except requests.RequestException:
                pass
            time.sleep(delay)
    if response.status_code == 429:
        raise ValueError("Rieltor тимчасово обмежив запити. Зачекайте 1–2 хвилини й повторіть спробу.")
    response.raise_for_status()
    parser = ListingParser()
    parser.feed(response.text)
    title = first(parser.meta, "og:title", "twitter:title") or parser.title.strip()
    description = first(parser.meta, "og:description", "description", "twitter:description")
    # Rieltor's OG description is only a short price/area summary; its full text
    # is in .offer-view-section-text and is stored first by ListingParser.
    page_text = "\n\n".join(parser.text_blocks[:12])
    if (urlparse(response.url).hostname or "").endswith("rieltor.ua") and parser.text_blocks:
        description = page_text
    else:
        description = description or page_text
    images = parser.meta.get("og:image", []) + parser.meta.get("twitter:image", []) + parser.images
    for item in flatten_jsonld(parser.json_ld):
        title = title or str(item.get("name", ""))
        description = description or str(item.get("description", ""))
        image = item.get("image", [])
        images.extend(image if isinstance(image, list) else [image])
    clean_images = []
    for image in images:
        if isinstance(image, dict): image = image.get("url", "")
        if isinstance(image, str):
            absolute = urljoin(response.url, image)
            if absolute.startswith("https://") and absolute not in clean_images:
                clean_images.append(absolute)
    blocked_markers = ("just a moment", "access denied", "checking your browser", "captcha")
    if not title or any(marker in title.lower() for marker in blocked_markers):
        raise ValueError("Не вдалося прочитати оголошення. Можливо, сайт запросив перевірку або змінив розмітку.")
    listing = {"title": html.unescape(title).strip(), "description": html.unescape(description).strip(), "images": clean_images[:20], "source": response.url}
    LISTING_CACHE[cache_key] = (time.time(), listing)
    return listing


def token():
    global ACCESS_TOKEN
    if ACCESS_TOKEN:
        return ACCESS_TOKEN
    result = requests.post(f"{TELEGRAPH_API}/createAccount", json={"short_name": "ListingMaker"}, timeout=15).json()
    if not result.get("ok"):
        raise RuntimeError("Telegraph не надав токен.")
    ACCESS_TOKEN = result["result"]["access_token"]
    return ACCESS_TOKEN


def publish(payload):
    title = str(payload.get("title", "")).strip()
    text = str(payload.get("text", "")).strip()
    source = str(payload.get("source", "")).strip()
    images = payload.get("images", [])
    if not title or not isinstance(images, list):
        raise ValueError("Потрібні заголовок і коректний список фотографій.")
    content = []
    for paragraph in text.splitlines():
        if paragraph.strip(): content.append({"tag": "p", "children": [paragraph.strip()]})
    for image in images[:20]:
        if isinstance(image, str) and image.startswith("https://"):
            content.append({"tag": "img", "attrs": {"src": image}})
    if source:
        content.append({"tag": "p", "children": [{"tag": "a", "attrs": {"href": source}, "children": ["Джерело: оголошення"]}]})
    result = requests.post(f"{TELEGRAPH_API}/createPage", json={"access_token": token(), "title": title[:256], "content": json.dumps(content, ensure_ascii=False), "return_content": False}, timeout=25).json()
    if not result.get("ok"):
        raise RuntimeError(result.get("error", "Telegraph не зміг створити сторінку."))
    return result["result"]["url"]


def reply(start_response, status, data):
    body = json.dumps(data, ensure_ascii=False).encode()
    start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def app(environ, start_response):
    path, method = environ["PATH_INFO"], environ["REQUEST_METHOD"]
    try:
        if path == "/" and method == "GET":
            body = (ROOT / "index.html").read_bytes()
            start_response("200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))])
            return [body]
        if path in {"/api/extract", "/api/publish"} and method == "POST":
            length = int(environ.get("CONTENT_LENGTH") or 0)
            payload = json.loads(environ["wsgi.input"].read(length) or b"{}")
            return reply(start_response, "200 OK", extract_listing(payload.get("url", "")) if path.endswith("extract") else {"url": publish(payload)})
        return reply(start_response, "404 Not Found", {"error": "Не знайдено"})
    except (ValueError, requests.RequestException, RuntimeError) as error:
        return reply(start_response, "400 Bad Request", {"error": str(error)})
    except Exception:
        return reply(start_response, "500 Internal Server Error", {"error": "Внутрішня помилка сервісу."})


if __name__ == "__main__":
    print(f"Open http://localhost:{PORT}")
    make_server("0.0.0.0", PORT, app).serve_forever()
