import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from ai_tutor import (
    ASK_AI,
    EXIT_AI,
    answer_question,
    close_ai_chat,
    open_ai_chat,
    show_ai_hint,
)
from cpp_lessons import CPP_PAGES
from math_lessons import MATH_PAGES


SUBJECTS = {"Программирование": "cpp", "Математика": "math"}
LESSON_PAGES = {"cpp": CPP_PAGES, "math": MATH_PAGES}
main_menu = ReplyKeyboardMarkup([list(SUBJECTS), [ASK_AI]], resize_keyboard=True)


def lesson_keyboard(subject: str, rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=f"{subject}:{page}") for label, page in row]
        for row in rows
    ])


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    close_ai_chat(context, update.message.chat_id)
    await update.message.reply_text(
        "Привет! Я помогу тебе практиковаться в программировании и математике. "
        "Выбери предмет или задай вопрос ИИ.",
        reply_markup=main_menu,
    )


async def select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if close_ai_chat(context, message.chat_id):
        await message.reply_text("Ты вернулся к урокам.", reply_markup=main_menu)
    subject = SUBJECTS[message.text]
    text, rows = LESSON_PAGES[subject]["menu"]
    await message.reply_text(text, reply_markup=lesson_keyboard(subject, rows))


async def show_lesson_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subject, page = query.data.split(":", 1)
    pages = LESSON_PAGES[subject]
    if page in pages:
        text, rows = pages[page]
        await query.edit_message_text(
            text,
            reply_markup=lesson_keyboard(subject, rows),
            parse_mode="HTML" if subject == "cpp" else None,
        )


def main() -> None:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit("Добавь BOT_TOKEN в файл .env рядом с main.py.")

    app = Application.builder().token(token).build()
    new_messages = filters.UpdateType.MESSAGE
    app.add_handler(CommandHandler("start", show_menu, filters=new_messages))
    app.add_handler(MessageHandler(new_messages & filters.Text([EXIT_AI]), show_menu))
    app.add_handler(MessageHandler(new_messages & filters.Text([ASK_AI]), open_ai_chat))
    app.add_handler(MessageHandler(new_messages & filters.Text(list(SUBJECTS)), select_subject))
    app.add_handler(CallbackQueryHandler(show_ai_hint, pattern=r"^(cpp|math):ai$", block=False))
    app.add_handler(CallbackQueryHandler(open_ai_chat, pattern=r"^ask:(cpp|math)$"))
    app.add_handler(CallbackQueryHandler(show_lesson_page, pattern=r"^(cpp|math):"))
    app.add_handler(
        MessageHandler(new_messages & filters.TEXT & ~filters.COMMAND, answer_question, block=False)
    )
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
