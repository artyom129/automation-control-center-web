from __future__ import annotations

import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://books.toscrape.com/"
COLUMNS = ["title", "price", "availability", "rating", "product_url"]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36"
}


def fetch_page(url: str) -> BeautifulSoup:
    response = requests.get(url, headers=HEADERS, timeout=20)
    response.raise_for_status()
    # Raw bytes let BeautifulSoup read the charset from the page. response.text
    # guesses ISO-8859-1 here, which turns "£" into "Â£".
    return BeautifulSoup(response.content, "html.parser")


def extract_rating(article) -> str:
    rating = article.select_one(".star-rating")
    if not rating:
        return ""

    for item in rating.get("class", []):
        if item != "star-rating":
            return item

    return ""


def parse_products(soup: BeautifulSoup, current_url: str) -> list[dict[str, str]]:
    products = []

    for article in soup.select("article.product_pod"):
        title = article.select_one("h3 a")
        price = article.select_one(".price_color")
        availability = article.select_one(".availability")
        href = title.get("href", "") if title else ""

        products.append({
            "title": title.get("title", "").strip() if title else "",
            "price": price.get_text(strip=True) if price else "",
            "availability": availability.get_text(" ", strip=True) if availability else "",
            "rating": extract_rating(article),
            "product_url": urljoin(current_url, href) if href else "",
        })

    return products


def find_next_page(soup: BeautifulSoup, current_url: str) -> str | None:
    next_link = soup.select_one("li.next a")
    if not next_link:
        return None

    href = next_link.get("href")
    if not href:
        return None

    return urljoin(current_url, href)


def scrape_demo_products(max_pages: int = 2, delay_seconds: float = 0.4) -> pd.DataFrame:
    all_products: list[dict[str, str]] = []
    visited: set[str] = set()
    current_url: str | None = BASE_URL
    page = 1

    while current_url and current_url not in visited and page <= max_pages:
        visited.add(current_url)
        soup = fetch_page(current_url)
        all_products.extend(parse_products(soup, current_url))
        current_url = find_next_page(soup, current_url)
        page += 1

        if current_url and delay_seconds > 0:
            time.sleep(delay_seconds)

    df = pd.DataFrame(all_products, columns=COLUMNS)
    df = df[df["product_url"] != ""].drop_duplicates(subset=["product_url"])
    return df.reset_index(drop=True)
