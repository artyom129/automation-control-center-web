# Automation Control Center Web

A Python Flask web dashboard for running common business automation tasks from one clean interface.

This project combines CSV/Excel data cleaning, API data synchronization, website scraping, SQLite run history, and export tools into a single local web application.

## Features

- CSV data cleaning
- Duplicate row detection and removal
- Invalid row separation
- Excel report generation
- API data sync workflow
- Website scraping to CSV
- SQLite run history
- CSV and Excel exports
- Clean Flask web interface
- English / Russian language toggle
- Separate HTML and CSS structure

## Tech Stack

- Python
- Flask
- Pandas
- SQLite
- OpenPyXL
- Requests
- BeautifulSoup
- HTML
- CSS

## What This Project Solves

Many small businesses work with messy CSV files, repeated manual data cleanup, API exports, and basic web data collection.

This dashboard gives a simple way to run these automation tasks from one place without manually editing files every time.

The main workflow is:

1. Upload or process data
2. Clean and validate records
3. Remove duplicates
4. Store run history
5. Export clean CSV / Excel reports

## Main Modules

### CSV Cleaner

Cleans CSV files, removes duplicates, validates fields, and separates invalid rows.

### API Data Sync

Imports data from an API, normalizes records, stores results, and exports clean reports.

### Website Scraper

Scrapes structured website data and exports it into CSV format.

### Run History

Stores automation runs in SQLite so previous tasks can be reviewed later.

## How To Run

Clone the repository:

```bash
git clone https://github.com/artyom129/automation-control-center-web.git
cd automation-control-center-web/automation_control_center_web
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python app.py
```

Open in browser:

```bash
http://127.0.0.1:5000
```

## Why I Built This

I built this project as a portfolio-ready Python automation tool to show practical experience with data processing, local dashboards, file automation, API workflows, and export systems.

The goal was to create something useful, clean, and close to real freelance automation tasks.

## Author

Artyom K.  
Python Automation Developer

GitHub: https://github.com/artyom129
