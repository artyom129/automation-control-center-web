import io

import pandas as pd
import pytest
import requests
from openpyxl import load_workbook

import app as app_module
from modules import database

PAGES = ["/", "/csv", "/api", "/scraper", "/history", "/help"]


@pytest.mark.parametrize("path", PAGES)
def test_every_page_renders(client, path):
    response = client.get(path)

    assert response.status_code == 200
    assert b"Automation Center" in response.data


def test_language_toggle_switches_the_interface(client):
    assert "Обзор" in client.get("/?lang=ru").get_data(as_text=True)
    assert "Overview" in client.get("/?lang=en").get_data(as_text=True)
    # the choice is remembered in the session
    assert "Overview" in client.get("/csv").get_data(as_text=True)


def test_unknown_language_is_ignored(client):
    assert client.get("/?lang=xx").status_code == 200


def test_csv_sample_run_shows_results_and_creates_files(client, tmp_path):
    client.get("/?lang=en")
    response = client.post("/csv", data={"action": "sample"})
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Download CSV" in html
    assert "john@example.com" in html
    assert (tmp_path / "output" / "cleaned_data.csv").exists()

    wb = load_workbook(tmp_path / "output" / "cleaned_data_report.xlsx")
    assert wb["Dashboard"]["B3"].value == 4
    assert wb["Dashboard"]["B4"].value == 1


def test_csv_upload_is_cleaned(client):
    data = {"csv_file": (io.BytesIO(b"name,email\n bob ,BOB@X.COM\nann,bad\n"), "people.csv")}
    response = client.post("/csv", data=data, content_type="multipart/form-data")
    html = response.get_data(as_text=True)

    assert "bob@x.com" in html
    assert "Invalid email" in html


def test_runs_appear_in_history_and_on_the_dashboard(client):
    client.get("/?lang=en")
    client.post("/csv", data={"action": "sample"})

    assert "CSV Cleaner" in client.get("/history").get_data(as_text=True)
    dashboard = client.get("/").get_data(as_text=True)
    assert "Total runs" in dashboard
    assert "CSV Cleaner" in dashboard


@pytest.mark.parametrize("payload, filename, expected", [
    (None, None, "No CSV file was selected."),
    (b"a,b\n1,2\n", "data.txt", "must have a .csv extension"),
    (b"", "empty.csv", "contains no data"),
    (b"\xff\xfe\x00bad", "latin.csv", "could not be read"),
])
def test_bad_uploads_show_a_friendly_message(client, payload, filename, expected):
    client.get("/?lang=en")
    data = {} if payload is None else {"csv_file": (io.BytesIO(payload), filename)}
    response = client.post("/csv", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    assert expected in response.get_data(as_text=True)
    assert "Traceback" not in response.get_data(as_text=True)


def test_oversized_upload_is_rejected(client, monkeypatch):
    monkeypatch.setitem(app_module.app.config, "MAX_CONTENT_LENGTH", 100)
    client.get("/?lang=en")
    data = {"csv_file": (io.BytesIO(b"name,email\n" + b"a,b@c.d\n" * 100), "big.csv")}
    response = client.post("/csv", data=data, content_type="multipart/form-data")

    assert response.status_code == 413
    assert "too large" in response.get_data(as_text=True)


def test_api_sync_with_mocked_api(client, monkeypatch):
    records = [
        {"id": 1, "name": "ann lee", "email": "ANN@x.com", "address": {"city": "Rome"}},
        {"id": 2, "name": "ann copy", "email": "ann@x.com"},
        {"id": 3, "name": "Broken", "email": "nope"},
    ]
    monkeypatch.setattr(app_module, "fetch_api_records", lambda: records)
    client.get("/?lang=en")
    html = client.post("/api").get_data(as_text=True)

    assert "Ann Lee" in html
    assert "Rome" in html


def test_api_failure_is_logged_and_shown(client, monkeypatch):
    def down():
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(app_module, "fetch_api_records", down)
    client.get("/?lang=en")
    html = client.post("/api").get_data(as_text=True)

    assert "offline" in html
    assert database.get_recent_runs()[0]["status"] == "Failed"


def test_scraper_page_limit_is_clamped(client, monkeypatch):
    seen = []

    def fake_scrape(max_pages):
        seen.append(max_pages)
        return pd.DataFrame({"title": ["Book"], "price": ["£1.00"]})

    monkeypatch.setattr(app_module, "scrape_demo_products", fake_scrape)
    client.get("/?lang=en")
    client.post("/scraper", data={"pages": "99"})
    client.post("/scraper", data={"pages": "0"})

    assert seen == [5, 1]


def test_download_serves_generated_files_and_ignores_unknown_ones(client):
    client.post("/csv", data={"action": "sample"})

    ok = client.get("/download/cleaned_data.csv")
    assert ok.status_code == 200
    assert b"john@example.com" in ok.data

    assert client.get("/download/nope.csv").status_code == 302


def test_download_cannot_escape_the_output_folder(client, tmp_path):
    (tmp_path / "secret.txt").write_text("secret")
    response = client.get("/download/..%2Fsecret.txt")

    assert b"secret" not in response.data
