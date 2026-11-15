import os

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from math_lessons import open_math_menu, show_math_page


SUBJECTS = ("Программирование", "Математика")
main_menu = ReplyKeyboardMarkup([SUBJECTS], resize_keyboard=True)


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу тебе практиковаться в программировании и математике. "
        "Выбери предмет.",
        reply_markup=main_menu,
    )


async def select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message.text == "Математика":
        await open_math_menu(message)
        return

    await message.reply_text(f"Ты выбрал раздел «{message.text}». Здесь появятся уроки.")


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Добавь BOT_TOKEN в файл .env рядом с main.py.")

    app = Application.builder().token(token).build()
    new_messages = filters.UpdateType.MESSAGE
    app.add_handler(CommandHandler("start", show_menu, filters=new_messages))
    app.add_handler(MessageHandler(new_messages & filters.Text(SUBJECTS), select_subject))
    app.add_handler(CallbackQueryHandler(show_math_page, pattern=r"^math:"))
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
