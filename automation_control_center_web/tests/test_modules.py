import json
import sqlite3
from contextlib import closing

import pandas as pd
import pytest
from bs4 import BeautifulSoup
from openpyxl import load_workbook

from modules import api_sync, database, web_scraper
from modules.csv_cleaner import clean_dataframe, normalize_column_names
from modules.excel_report import create_excel_report


# --------------------------------------------------------------------------
# CSV cleaner
# --------------------------------------------------------------------------

def test_column_names_are_normalized():
    df = pd.DataFrame(columns=[" First Name ", "E-mail", "Amount"])

    assert list(normalize_column_names(df).columns) == ["first_name", "e_mail", "amount"]


def test_cleaner_trims_titles_and_lowercases():
    df = pd.DataFrame({"name": ["  john smith "], "email": [" JOHN@Example.com "],
                       "company": ["alpha agency"]})
    clean, invalid, _ = clean_dataframe(df)

    assert clean.loc[0, "name"] == "John Smith"
    assert clean.loc[0, "email"] == "john@example.com"
    assert clean.loc[0, "company"] == "Alpha Agency"
    assert invalid.empty


def test_duplicate_under_a_new_id_is_removed():
    df = pd.DataFrame({"id": [1, 2], "name": ["Ann", " ann "], "email": ["a@x.com", "A@x.com"]})
    clean, _, stats = clean_dataframe(df)

    assert len(clean) == 1
    assert stats["duplicates_removed"] == 1


def test_invalid_emails_are_separated_with_a_reason():
    df = pd.DataFrame({"name": ["Ann", "Bob"], "email": ["a@x.com", "not-an-email"]})
    clean, invalid, stats = clean_dataframe(df)

    assert list(clean["name"]) == ["Ann"]
    assert list(invalid["error"]) == ["Invalid email"]
    assert stats == {"total_rows": 2, "clean_rows": 1, "invalid_rows": 1, "duplicates_removed": 0}


def test_missing_email_values_are_invalid_not_a_crash():
    df = pd.DataFrame({"name": ["Ann"], "email": [None]})
    _, invalid, _ = clean_dataframe(df)

    assert len(invalid) == 1


def test_file_without_an_email_column_is_all_clean():
    df = pd.DataFrame({"name": ["Ann", "Bob"]})
    clean, invalid, _ = clean_dataframe(df)

    assert len(clean) == 2
    assert invalid.empty


def test_sample_file_gives_the_documented_numbers():
    df = pd.read_csv("sample_data/sample_customers.csv")
    _, _, stats = clean_dataframe(df)

    assert stats == {"total_rows": 6, "clean_rows": 4, "invalid_rows": 1, "duplicates_removed": 1}


# --------------------------------------------------------------------------
# API sync
# --------------------------------------------------------------------------

def api_item(i, email, name="Test User", **extra):
    return {"id": i, "name": name, "username": "u", "email": email, **extra}


def test_missing_api_fields_do_not_become_the_word_none():
    clean, _ = api_sync.normalize_api_records([api_item(1, "a@x.com", phone=None)])

    assert clean.loc[0, "phone"] == ""
    assert clean.loc[0, "city"] == ""


def test_api_duplicates_and_all_errors_are_reported():
    clean, invalid = api_sync.normalize_api_records([
        api_item(1, "a@x.com"),
        api_item(2, "A@x.com"),
        api_item(1, "b@x.com"),
        {"id": "", "name": "", "email": "bad"},
        "junk",
    ])

    assert list(clean["source_id"]) == ["1"]
    assert list(invalid["error"]) == [
        "Duplicate email",
        "Duplicate source id",
        "Missing source id; Missing name; Invalid email",
        "Record is not an object",
    ]


def test_empty_api_result_gives_empty_frames():
    clean, invalid = api_sync.normalize_api_records([])

    assert clean.empty and invalid.empty


def test_fetch_rejects_non_list_payloads(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"error": "nope"}

    monkeypatch.setattr(api_sync.requests, "get", lambda *a, **k: Response())

    with pytest.raises(ValueError):
        api_sync.fetch_api_records()


# --------------------------------------------------------------------------
# Scraper
# --------------------------------------------------------------------------

def listing(items, next_href=None):
    cards = "".join(
        f'<article class="product_pod"><p class="star-rating Two"></p>'
        f'<h3><a href="{href}" title="{title}">x</a></h3>'
        f'<p class="price_color">£1.00</p><p class="availability"> In stock </p></article>'
        for title, href in items)
    nxt = f'<li class="next"><a href="{next_href}">n</a></li>' if next_href else ""
    return BeautifulSoup(f"<body>{cards}<ul>{nxt}</ul></body>", "html.parser")


def test_scraper_resolves_links_against_the_current_page(monkeypatch):
    pages = {
        web_scraper.BASE_URL: listing([("One", "catalogue/one_1/index.html")],
                                      next_href="catalogue/page-2.html"),
        web_scraper.BASE_URL + "catalogue/page-2.html": listing([("Two", "two_2/index.html")]),
    }
    monkeypatch.setattr(web_scraper, "fetch_page", lambda url: pages[url])

    df = web_scraper.scrape_demo_products(max_pages=5, delay_seconds=0)

    assert list(df["product_url"]) == [
        "https://books.toscrape.com/catalogue/one_1/index.html",
        "https://books.toscrape.com/catalogue/two_2/index.html",
    ]
    assert df.loc[0, "availability"] == "In stock"


def test_scraper_stops_on_pagination_loops(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return listing([("One", "one_1/index.html")], next_href=url)

    monkeypatch.setattr(web_scraper, "fetch_page", fake_fetch)
    df = web_scraper.scrape_demo_products(max_pages=5, delay_seconds=0)

    assert len(calls) == 1
    assert len(df) == 1


def test_scraper_respects_the_page_limit(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return listing([(f"Book {len(calls)}", f"b{len(calls)}/index.html")],
                       next_href=f"page-{len(calls) + 1}.html")

    monkeypatch.setattr(web_scraper, "fetch_page", fake_fetch)
    df = web_scraper.scrape_demo_products(max_pages=2, delay_seconds=0)

    assert len(calls) == 2
    assert len(df) == 2


def test_scraper_fetch_reads_the_charset_from_the_page(monkeypatch):
    class Response:
        content = '<meta charset="utf-8"><p class="price_color">£5.00</p>'.encode()

        def raise_for_status(self):
            pass

    monkeypatch.setattr(web_scraper.requests, "get", lambda *a, **k: Response())

    assert web_scraper.fetch_page("https://x.test/").select_one(".price_color").text == "£5.00"


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "nested" / "t.db")
    return database


def test_database_is_created_on_first_use(db):
    assert db.get_recent_runs() == []
    assert db.DATABASE_FILE.exists()


def test_runs_are_returned_newest_first_and_summarized(db):
    db.save_run_log("CSV Cleaner", "Success", 10)
    db.save_run_log("API Sync", "Failed", 0, "boom")
    db.save_run_log("Website Scraper", "Success", 5)

    runs = db.get_recent_runs()
    assert [r["task_name"] for r in runs] == ["Website Scraper", "API Sync", "CSV Cleaner"]
    assert db.get_run_summary() == {"total_runs": 3, "successful": 2, "failed": 1, "records": 15}


def test_clean_records_are_stored_as_valid_json(db):
    df = pd.DataFrame({"name": ["Ann"], "amount": [1.5], "note": [None]})
    db.save_clean_records(df, "test")

    with closing(sqlite3.connect(db.DATABASE_FILE)) as conn:
        (raw,) = conn.execute("SELECT record_json FROM clean_records").fetchone()
    assert json.loads(raw)["name"] == "Ann"


def test_saving_an_empty_frame_is_a_no_op(db):
    db.save_clean_records(pd.DataFrame(), "test")

    assert db.get_run_summary()["total_runs"] == 0


# --------------------------------------------------------------------------
# Excel report
# --------------------------------------------------------------------------

def test_excel_report_has_three_sheets_and_correct_counts(tmp_path):
    clean = pd.DataFrame({"name": ["Ann", "Bob"]})
    invalid = pd.DataFrame({"name": ["Cy"], "error": ["Invalid email"]})
    path = tmp_path / "sub" / "report.xlsx"

    create_excel_report(clean, invalid, path, "My Report")
    wb = load_workbook(path)

    assert wb.sheetnames == ["Dashboard", "Clean Records", "Invalid Records"]
    assert wb["Dashboard"]["A1"].value == "My Report"
    assert wb["Dashboard"]["B3"].value == 2
    assert wb["Dashboard"]["B4"].value == 1
    assert wb["Clean Records"]["A2"].value == "Ann"


def test_empty_frames_produce_a_readable_sheet(tmp_path):
    path = tmp_path / "report.xlsx"
    create_excel_report(pd.DataFrame(), pd.DataFrame(), path, "Empty")

    assert load_workbook(path)["Clean Records"]["A1"].value == "No records"
