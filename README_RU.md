# Automation Control Center Web

[English](README.md) | **Русский**

Локальная веб-панель на Flask для запуска типовых задач бизнес-автоматизации из одного интерфейса.

Проект объединяет очистку CSV/Excel, синхронизацию данных через API, веб-скрапинг, историю запусков в SQLite и экспорт результатов.

## Возможности

- очистка CSV;
- поиск и удаление дублей;
- отделение некорректных строк;
- генерация Excel-отчётов;
- синхронизация данных через API;
- веб-скрапинг в CSV;
- история запусков в SQLite;
- экспорт CSV и Excel;
- Flask-интерфейс;
- переключение English / Русский;
- раздельные HTML и CSS.

## Стек

Python, Flask, Pandas, SQLite, OpenPyXL, Requests, BeautifulSoup, HTML, CSS.

## Основной сценарий

1. Загрузить или получить данные.
2. Очистить и проверить записи.
3. Удалить дубли.
4. Сохранить историю запуска.
5. Экспортировать готовый CSV или Excel.

## Запуск

```bash
git clone https://github.com/artyom129/automation-control-center-web.git
cd automation-control-center-web/automation_control_center_web
pip install -r requirements.txt
python app.py
```

Открыть:

```text
http://127.0.0.1:5000
```

Проект создан как демонстрация практической Python-автоматизации, обработки данных, API-процессов и локальных бизнес-панелей.
