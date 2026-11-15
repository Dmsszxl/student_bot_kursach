# Бот для первокурсников

Курсовой проект: Telegram-бот для обучения программированию и математике.

## Локальный запуск

Получи токен у [@BotFather](https://t.me/BotFather) и добавь строку `BOT_TOKEN=твой_токен` в файл `.env` в папке проекта.

При первом запуске создай окружение и установи зависимости.

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

Для запуска из нового окна терминала выполни в папке проекта:

```bash
source venv/bin/activate
python main.py
```

В Telegram отправь боту `/start`. Для остановки нажми `Control+C` в терминале.
