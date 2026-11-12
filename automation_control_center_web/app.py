from __future__ import annotations

import os
import secrets
from pathlib import Path

import pandas as pd
from flask import Flask, redirect, render_template, request, send_file, session, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

from modules.api_sync import fetch_api_records, normalize_api_records
from modules.csv_cleaner import clean_dataframe
from modules.database import (
    create_tables,
    get_recent_runs,
    get_run_summary,
    save_clean_records,
    save_run_log,
)
from modules.excel_report import create_excel_report
from modules.web_scraper import scrape_demo_products


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
MAX_UPLOAD_MB = 5

app = Flask(__name__)
# Set SECRET_KEY in the environment for a stable session across restarts.
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(16)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


TEXT = {
    "ru": {
        "product": "Automation Center",
        "subtitle": "Панель для автоматизации данных",
        "dashboard": "Обзор",
        "csv": "CSV очистка",
        "api": "API данные",
        "scraper": "Парсер",
        "history": "История",
        "help": "Помощь",
        "language": "Язык",
        "overview_title": "Обзор",
        "overview_text": "Рабочая панель для обработки таблиц, загрузки данных из API, парсинга сайта и выгрузки результатов в CSV/Excel.",
        "csv_title": "CSV очистка",
        "csv_text": "Загрузите CSV-файл или используйте тестовый пример. Система удалит дубли, проверит email и подготовит отчёты.",
        "api_title": "API данные",
        "api_text": "Загрузка тестовых данных из REST API, очистка, сохранение в SQLite и экспорт результата.",
        "scraper_title": "Парсер сайта",
        "scraper_text": "Сбор данных с демо-сайта с поддержкой пагинации и экспортом в CSV/Excel.",
        "history_title": "История запусков",
        "history_text": "Список последних операций, статусы, количество обработанных строк и детали.",
        "help_title": "Как пользоваться",
        "help_text": [
            "Выберите нужный раздел в меню слева.",
            "В CSV очистке можно загрузить свой файл или запустить тестовый пример.",
            "В API и парсере нажмите кнопку запуска.",
            "После обработки скачайте CSV или Excel.",
            "История запусков сохраняется автоматически.",
        ],
        "open": "Открыть",
        "run_sample": "Запустить тестовый пример",
        "upload_file": "Загрузить файл",
        "choose_file": "Выберите CSV",
        "run_api": "Запустить API обработку",
        "run_scraper": "Запустить парсер",
        "pages": "Количество страниц",
        "raw_data": "Исходные данные",
        "clean_data": "Готовые данные",
        "invalid_data": "Ошибочные строки",
        "results": "Результаты",
        "download_csv": "Скачать CSV",
        "download_excel": "Скачать Excel",
        "total": "Всего строк",
        "ready": "Готово",
        "duplicates": "Дубли",
        "errors": "Ошибки",
        "recent_runs": "Последние запуски",
        "no_data": "Данных пока нет.",
        "done": "Готово",
        "failed": "Ошибка",
        "status": "Статус",
        "records": "Записей",
        "details": "Детали",
        "created": "Дата",
        "task": "Задача",
        "total_runs": "Всего запусков",
        "successful_runs": "Успешных",
        "failed_runs": "С ошибкой",
        "records_processed": "Обработано записей",
        "err_no_file": "Файл CSV не выбран.",
        "err_not_csv": "Нужен файл с расширением .csv.",
        "err_empty_csv": "В файле нет данных.",
        "err_bad_csv": "Не удалось прочитать файл как CSV в кодировке UTF-8.",
        "err_too_large": "Файл слишком большой (максимум {mb} МБ).",
    },
    "en": {
        "product": "Automation Center",
        "subtitle": "Data automation dashboard",
        "dashboard": "Overview",
        "csv": "CSV Cleaner",
        "api": "API Data",
        "scraper": "Scraper",
        "history": "History",
        "help": "Help",
        "language": "Language",
        "overview_title": "Overview",
        "overview_text": "A working dashboard for spreadsheet processing, API data loading, website scraping, and CSV/Excel exports.",
        "csv_title": "CSV Cleaner",
        "csv_text": "Upload a CSV file or use the sample dataset. The system removes duplicates, validates emails, and creates reports.",
        "api_title": "API Data",
        "api_text": "Load sample REST API data, clean it, store it in SQLite, and export the result.",
        "scraper_title": "Website Scraper",
        "scraper_text": "Collect data from a demo website with pagination support and export to CSV/Excel.",
        "history_title": "Run History",
        "history_text": "Recent operations, statuses, processed records, and details.",
        "help_title": "How to use",
        "help_text": [
            "Choose a section from the left menu.",
            "In CSV Cleaner, upload your own file or run the sample dataset.",
            "In API and Scraper sections, press the run button.",
            "Download CSV or Excel after processing.",
            "Run history is saved automatically.",
        ],
        "open": "Open",
        "run_sample": "Run sample",
        "upload_file": "Upload file",
        "choose_file": "Choose CSV",
        "run_api": "Run API processing",
        "run_scraper": "Run scraper",
        "pages": "Number of pages",
        "raw_data": "Raw data",
        "clean_data": "Ready data",
        "invalid_data": "Invalid rows",
        "results": "Results",
        "download_csv": "Download CSV",
        "download_excel": "Download Excel",
        "total": "Total rows",
        "ready": "Ready",
        "duplicates": "Duplicates",
        "errors": "Errors",
        "recent_runs": "Recent runs",
        "no_data": "No data yet.",
        "done": "Done",
        "failed": "Error",
        "status": "Status",
        "records": "Records",
        "details": "Details",
        "created": "Created",
        "task": "Task",
        "total_runs": "Total runs",
        "successful_runs": "Successful",
        "failed_runs": "Failed",
        "records_processed": "Records processed",
        "err_no_file": "No CSV file was selected.",
        "err_not_csv": "The file must have a .csv extension.",
        "err_empty_csv": "The file contains no data.",
        "err_bad_csv": "The file could not be read as a UTF-8 CSV.",
        "err_too_large": "The file is too large (limit {mb} MB).",
    },
}


def get_lang() -> str:
    lang = request.args.get("lang")
    if lang in TEXT:
        session["lang"] = lang
    return session.get("lang", "ru")


@app.context_processor
def inject_globals():
    lang = get_lang()
    return {
        "t": TEXT[lang],
        "lang": lang,
    }


class UserInputError(Exception):
    """A problem with the user's input, shown as-is instead of a traceback."""


def read_uploaded_csv(uploaded, t: dict) -> tuple[pd.DataFrame, str]:
    if uploaded is None or uploaded.filename == "":
        raise UserInputError(t["err_no_file"])

    filename = secure_filename(uploaded.filename)
    if not filename.lower().endswith(".csv"):
        raise UserInputError(t["err_not_csv"])

    try:
        # Read straight from the request stream, nothing is written to disk.
        return pd.read_csv(uploaded.stream), filename
    except pd.errors.EmptyDataError:
        raise UserInputError(t["err_empty_csv"]) from None
    except (UnicodeDecodeError, pd.errors.ParserError):
        raise UserInputError(t["err_bad_csv"]) from None


@app.errorhandler(413)
def file_too_large(_error):
    t = TEXT[get_lang()]
    return render_template(
        "csv.html", active="csv", raw_table=None, clean_table=None,
        invalid_table=None, stats=None, downloads=None, message=None,
        error=t["err_too_large"].format(mb=MAX_UPLOAD_MB),
    ), 413


@app.route("/")
def dashboard():
    runs = get_recent_runs(limit=5)
    return render_template("dashboard.html", active="dashboard", runs=runs,
                           summary=get_run_summary())


@app.route("/csv", methods=["GET", "POST"])
def csv_cleaner():
    context = {
        "active": "csv",
        "raw_table": None,
        "clean_table": None,
        "invalid_table": None,
        "stats": None,
        "downloads": None,
        "message": None,
        "error": None,
    }

    if request.method == "POST":
        try:
            source_name = "sample_customers.csv"

            if request.form.get("action") == "sample":
                df = pd.read_csv(SAMPLE_DATA_DIR / "sample_customers.csv")
            else:
                df, source_name = read_uploaded_csv(
                    request.files.get("csv_file"), TEXT[get_lang()])

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            clean_df, invalid_df, stats = clean_dataframe(df)

            csv_path = OUTPUT_DIR / "cleaned_data.csv"
            excel_path = OUTPUT_DIR / "cleaned_data_report.xlsx"

            clean_df.to_csv(csv_path, index=False)
            create_excel_report(clean_df, invalid_df, excel_path, "CSV Cleaning Report")

            save_clean_records(clean_df, "csv_cleaner")
            save_run_log(
                "CSV Cleaner",
                "Success",
                stats["total_rows"],
                f"Source: {source_name}; clean: {stats['clean_rows']}; errors: {stats['invalid_rows']}",
            )

            context.update({
                "raw_table": df.head(50).to_html(classes="data-table", index=False),
                "clean_table": clean_df.head(100).to_html(classes="data-table", index=False),
                "invalid_table": invalid_df.to_html(classes="data-table", index=False) if not invalid_df.empty else None,
                "stats": {
                    "total": stats["total_rows"],
                    "ready": stats["clean_rows"],
                    "duplicates": stats["duplicates_removed"],
                    "errors": stats["invalid_rows"],
                },
                "downloads": {
                    "csv": "cleaned_data.csv",
                    "excel": "cleaned_data_report.xlsx",
                },
                "message": "done",
            })

        except HTTPException:
            raise  # for example 413 for a too-large upload, handled above
        except UserInputError as exc:
            context["error"] = str(exc)
        except Exception as exc:
            save_run_log("CSV Cleaner", "Failed", 0, str(exc))
            context["error"] = str(exc)

    return render_template("csv.html", **context)


@app.route("/api", methods=["GET", "POST"])
def api_sync():
    context = {
        "active": "api",
        "table": None,
        "stats": None,
        "downloads": None,
        "message": None,
        "error": None,
    }

    if request.method == "POST":
        try:
            records = fetch_api_records()
            clean_df, invalid_df = normalize_api_records(records)
            duplicates = (
                int(invalid_df["error"].str.contains("Duplicate").sum())
                if "error" in invalid_df.columns else 0
            )

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            csv_path = OUTPUT_DIR / "api_sync_records.csv"
            excel_path = OUTPUT_DIR / "api_sync_report.xlsx"

            clean_df.to_csv(csv_path, index=False)
            create_excel_report(clean_df, invalid_df, excel_path, "API Sync Report")

            save_clean_records(clean_df, "api_sync")
            save_run_log(
                "API Sync",
                "Success",
                len(records),
                f"Clean: {len(clean_df)}; errors: {len(invalid_df)}",
            )

            context.update({
                "table": clean_df.to_html(classes="data-table", index=False),
                "stats": {
                    "total": len(records),
                    "ready": len(clean_df),
                    "duplicates": duplicates,
                    "errors": len(invalid_df) - duplicates,
                },
                "downloads": {
                    "csv": "api_sync_records.csv",
                    "excel": "api_sync_report.xlsx",
                },
                "message": "done",
            })

        except Exception as exc:
            save_run_log("API Sync", "Failed", 0, str(exc))
            context["error"] = str(exc)

    return render_template("api.html", **context)


@app.route("/scraper", methods=["GET", "POST"])
def scraper():
    context = {
        "active": "scraper",
        "table": None,
        "stats": None,
        "downloads": None,
        "message": None,
        "error": None,
        "pages": 2,
    }

    if request.method == "POST":
        try:
            pages = int(request.form.get("pages", 2))
            pages = max(1, min(5, pages))
            df = scrape_demo_products(max_pages=pages)

            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            csv_path = OUTPUT_DIR / "scraped_products.csv"
            excel_path = OUTPUT_DIR / "scraped_products_report.xlsx"

            df.to_csv(csv_path, index=False)
            create_excel_report(df, pd.DataFrame(), excel_path, "Website Scraper Report")

            save_clean_records(df, "web_scraper")
            save_run_log("Website Scraper", "Success", len(df), f"Pages: {pages}")

            context.update({
                "table": df.to_html(classes="data-table", index=False),
                "stats": {
                    "total": len(df),
                    "ready": len(df),
                    "duplicates": 0,
                    "errors": 0,
                },
                "downloads": {
                    "csv": "scraped_products.csv",
                    "excel": "scraped_products_report.xlsx",
                },
                "message": "done",
                "pages": pages,
            })

        except Exception as exc:
            save_run_log("Website Scraper", "Failed", 0, str(exc))
            context["error"] = str(exc)

    return render_template("scraper.html", **context)


@app.route("/history")
def history():
    runs = get_recent_runs(limit=50)
    return render_template("history.html", active="history", runs=runs)


@app.route("/help")
def help_page():
    return render_template("help.html", active="help")


@app.route("/download/<filename>")
def download_file(filename: str):
    safe_name = secure_filename(filename)
    file_path = OUTPUT_DIR / safe_name

    if not file_path.exists():
        return redirect(url_for("dashboard"))

    return send_file(file_path, as_attachment=True)


if __name__ == "__main__":
    create_tables()
    # Debug mode exposes an interactive console, so it is opt-in:
    #   set FLASK_DEBUG=1 (Windows) or export FLASK_DEBUG=1 (macOS / Linux)
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
