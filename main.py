import os
import re
from fractions import Fraction
from html import escape

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
from cpp_lessons import CPP_EXERCISES, CPP_PAGES
from math_lessons import MATH_EXERCISES, MATH_PAGES


SUBJECT_BUTTONS = {"💻 Программирование": "cpp", "📐 Математика": "math"}
SUBJECTS = SUBJECT_BUTTONS | {"Программирование": "cpp", "Математика": "math"}
AI_BUTTON = f"💬 {ASK_AI}"
LESSON_PAGES = {"cpp": CPP_PAGES, "math": MATH_PAGES}
LESSON_EXERCISES = {"cpp": CPP_EXERCISES, "math": MATH_EXERCISES}
NUMBER_FORMAT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|[0-9]+\s*/\s*[0-9]+)")
main_menu = ReplyKeyboardMarkup([list(SUBJECT_BUTTONS), [AI_BUTTON]], resize_keyboard=True)
LESSON_BUTTONS = {
    "Справка": "📖 Справка",
    "Пример": "📝 Пример",
    "Решить задачу": "✏️ Решить задачу",
    "Объясни подробнее": "💬 Объясни подробнее",
    "Назад": "← Назад",
    "К теме": "← К теме",
    "К задачам": "← К задачам",
}


def lesson_keyboard(subject: str, rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(LESSON_BUTTONS.get(label, label), callback_data=f"{subject}:{page}")
            for label, page in row
        ]
        for row in rows
    ])


def format_lesson(text: str, subject: str) -> str:
    if subject == "math":
        text = escape(text)
    for status, heading in (("Верно!", "✅ Верно!"), ("Пока неверно.", "💡 Пока неверно")):
        if text.startswith(f"{status} "):
            return f"<b>{heading}</b>\n\n{text.removeprefix(status).lstrip()}"
    title, separator, body = text.partition("\n\n")
    return f"<b>{title}</b>{separator}{body}"


def close_exercise(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    context.user_data.get("active_exercises", {}).pop(chat_id, None)


async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    close_ai_chat(context, update.message.chat_id)
    close_exercise(context, update.message.chat_id)
    await update.message.reply_text(
        "<b>Привет! Что хочешь разобрать сегодня?</b>\n\n"
        "Выбери предмет или задай вопрос ИИ.",
        reply_markup=main_menu,
        parse_mode="HTML",
    )


async def select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    close_exercise(context, message.chat_id)
    if close_ai_chat(context, message.chat_id):
        await message.reply_text("Ты вернулся к урокам.", reply_markup=main_menu)
    subject = SUBJECTS[message.text]
    text, rows = LESSON_PAGES[subject]["menu"]
    await message.reply_text(
        format_lesson(text, subject), reply_markup=lesson_keyboard(subject, rows), parse_mode="HTML"
    )


async def show_lesson_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    subject, page = query.data.split(":", 1)
    pages = LESSON_PAGES[subject]
    if page not in pages:
        return

    chat_id = update.effective_chat.id
    close_exercise(context, chat_id)
    exercise = LESSON_EXERCISES[subject].get(page)
    if exercise is not None and not exercise.choices:
        if close_ai_chat(context, chat_id):
            await query.message.reply_text("Ты вернулся к задаче.", reply_markup=main_menu)
        context.user_data.setdefault("active_exercises", {})[chat_id] = (subject, page)
    text, rows = pages[page]
    await query.edit_message_text(
        format_lesson(text, subject),
        reply_markup=lesson_keyboard(subject, rows),
        parse_mode="HTML",
    )


async def start_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    close_exercise(context, update.effective_chat.id)
    await open_ai_chat(update, context)


async def answer_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    active = context.user_data.get("active_exercises", {}).get(message.chat_id)
    if active is None:
        await answer_question(update, context)
        return

    subject, page = active
    exercise = LESSON_EXERCISES[subject][page]
    text = message.text.strip().replace("−", "-")
    if isinstance(exercise.answer, str):
        lines = [line.strip() for line in text.splitlines()]
        if not lines:
            await message.reply_text(exercise.input_instruction)
            return
        correct = lines == exercise.answer.splitlines()
    else:
        text = text.replace(",", ".")
        try:
            number = Fraction("".join(text.split())) if NUMBER_FORMAT.fullmatch(text) else None
        except (ValueError, ZeroDivisionError):
            number = None
        if number is None:
            await message.reply_text(exercise.input_instruction)
            return
        correct = number == exercise.answer

    if correct:
        close_exercise(context, message.chat_id)
    result = f"{page}-right" if correct else f"{page}-wrong"
    text, rows = LESSON_PAGES[subject][result]
    await message.reply_text(
        format_lesson(text, subject), reply_markup=lesson_keyboard(subject, rows), parse_mode="HTML"
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
    app.add_handler(MessageHandler(new_messages & filters.Text([ASK_AI, AI_BUTTON]), start_ai_chat))
    app.add_handler(MessageHandler(new_messages & filters.Text(list(SUBJECTS)), select_subject))
    app.add_handler(
        CallbackQueryHandler(show_ai_hint, pattern=r"^(cpp|math):(?:[a-z-]+-q[0-9]+-)?ai$", block=False)
    )
    app.add_handler(CallbackQueryHandler(start_ai_chat, pattern=r"^ask:(cpp|math)(?::[a-z-]+-q[0-9]+)?$"))
    app.add_handler(CallbackQueryHandler(show_lesson_page, pattern=r"^(cpp|math):"))
    app.add_handler(
        MessageHandler(new_messages & filters.TEXT & ~filters.COMMAND, answer_text, block=False)
    )
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
