from __future__ import annotations

import time
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://books.toscrape.com/"


def fetch_page(url: str) -> BeautifulSoup:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_rating(article) -> str:
    rating = article.select_one(".star-rating")
    if not rating:
        return ""

    classes = rating.get("class", [])
    for item in classes:
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
            "product_url": urljoin(current_url, href),
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


def scrape_demo_products(max_pages: int = 2) -> pd.DataFrame:
    all_products = []
    current_url = BASE_URL
    page = 1

    while current_url and page <= max_pages:
        soup = fetch_page(current_url)
        all_products.extend(parse_products(soup, current_url))
        current_url = find_next_page(soup, current_url)
        page += 1

        if current_url:
            time.sleep(0.4)

    df = pd.DataFrame(all_products)

    if not df.empty and "product_url" in df.columns:
        df = df.drop_duplicates(subset=["product_url"])

    return df.reset_index(drop=True)
