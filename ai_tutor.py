import logging
import os
from dataclasses import dataclass, field

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletionMessageParam
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from cpp_lessons import EXERCISE_CODE


GROQ_MODEL = "openai/gpt-oss-120b"
ASK_AI = "Спросить ИИ"
EXIT_AI = "Выйти из ИИ"
HINT_TITLE = "Подсказка от ИИ"
ai_keyboard = ReplyKeyboardMarkup([[EXIT_AI]], resize_keyboard=True)

TUTOR_PROMPT = (
    "Ты учебный помощник первокурсника. Отвечай на русском и обращайся на ты. "
    "Начинай сразу с ответа на вопрос и объясняй понятным языком. "
    "Ответ будет показан в обычном сообщении Telegram. Пиши без HTML, Markdown и LaTeX. "
    "Формулы записывай в одну строку, например (a + b)/2. Для кода используй отступы "
    "и переносы строк, без обратных кавычек."
)
HINT_PROMPT = (
    f"{TUTOR_PROMPT} Дай подсказку до трёх предложений, которая помогает сделать следующий шаг. "
    "Не выдавай готовый ответ или полное решение."
)
EXERCISES = {
    "cpp": (
        f"Нужно предсказать вывод программы при вводе 4 9.\n{EXERCISE_CODE}\n"
        "Оставь студенту определение итоговой строки вывода."
    ),
    "math": (
        "Нужно доказать по индукции, что сумма первых n нечётных чисел равна n². "
        "База n = 1 уже проверена. Вопрос в том, какое слагаемое добавить "
        "к сумме первых k нечётных чисел при переходе к k + 1. "
        "Можно объяснить, какие числа уже входят в старую сумму. "
        "Оставь студенту вычисление нового слагаемого и завершение доказательства."
    ),
}
HINT_REQUESTS = {
    "cpp:ai": (
        "Студент должен предсказать вывод уже написанной программы. Подскажи, "
        "как мысленно сопоставить введённые числа с переменными по порядку после "
        "std::cin, а затем прочитать операции std::cout слева направо, учитывая "
        "явно выведенный пробел. Не предлагай менять код. Не копируй код, "
        "не перечисляй переменные в порядке вывода и не приводи строку результата. "
        f"Код задачи:\n{EXERCISE_CODE}"
    ),
    "math:ai": (
        "Студент решает задачу на индукцию для суммы первых n нечётных чисел. "
        "Объясни, почему при переходе от первых k чисел к первым k + 1 "
        "важно различать последнее число старой суммы и новое слагаемое. "
        "Предложи определить номер добавляемого числа и самостоятельно подставить "
        "его в 2n − 1. Не записывай формулу после подстановки или ответ."
    ),
}
logger = logging.getLogger(__name__)


@dataclass
class AiChat:
    context: list[ChatCompletionMessageParam]
    history: list[ChatCompletionMessageParam] = field(default_factory=list)
    waiting: bool = False


def close_ai_chat(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> bool:
    return context.user_data.get("ai_chats", {}).pop(chat_id, None) is not None


async def ask_groq(api_key: str, messages: list[ChatCompletionMessageParam]) -> str:
    try:
        async with AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=10.0,
            max_retries=0,
        ) as client:
            result = await client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                reasoning_effort="low",
                max_completion_tokens=1200,
                extra_body={"reasoning_format": "hidden"},
            )
    except OpenAIError as error:
        logger.warning("Ошибка Groq: %s", type(error).__name__)
        return ""
    if not result.choices:
        return ""
    answer = (result.choices[0].message.content or "").strip()
    return answer if len(answer) <= 3500 else answer[:3499] + "…"


async def open_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not isinstance(message, Message):
        if update.callback_query:
            await update.callback_query.answer("Открой подсказку ещё раз.")
        return

    messages: list[ChatCompletionMessageParam] = [{"role": "system", "content": TUTOR_PROMPT}]
    invite = "Напиши свой вопрос. Например, зачем в C++ нужен std::cin?"
    query = update.callback_query
    if query:
        title, _, hint = (message.text or "").partition("\n\n")
        if title != HINT_TITLE or not hint:
            await query.answer("Открой подсказку ещё раз.")
            return
        await query.answer()
        subject = query.data.split(":", 1)[1]
        messages = [
            {"role": "system", "content": (
                f"{TUTOR_PROMPT} Ответь на конкретное уточнение, не продолжая решение задачи "
                "за студента. Если студент просит готовый ответ, дай следующий шаг.\n\n"
                f"{EXERCISES[subject]}"
            )},
            {"role": "user", "content": "Дай подсказку по этой задаче."},
            {"role": "assistant", "content": hint},
        ]
        invite = "Напиши, что осталось непонятным в подсказке."

    if not os.getenv("GROQ_API_KEY", "").strip():
        await message.reply_text("ИИ сейчас недоступен. Попробуй позже.")
        return
    chats = context.user_data.setdefault("ai_chats", {})
    chats[message.chat_id] = AiChat(messages)
    await message.reply_text(invite, reply_markup=ai_keyboard)


async def answer_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    chats = context.user_data.get("ai_chats", {})
    chat = chats.get(message.chat_id)
    question = message.text.strip()
    if chat is None or not question:
        return
    if chat.waiting:
        await message.reply_text("Подожди ответа на предыдущий вопрос.")
        return

    chat.waiting = True
    try:
        question_message: ChatCompletionMessageParam = {"role": "user", "content": question}
        messages = [*chat.context, *chat.history, question_message]
        await message.chat.send_action(ChatAction.TYPING)
        if chats.get(message.chat_id) is not chat:
            return
        answer = await ask_groq(os.getenv("GROQ_API_KEY", "").strip(), messages)
        if chats.get(message.chat_id) is not chat:
            return
        if not answer:
            await message.reply_text("ИИ сейчас недоступен. Попробуй отправить вопрос ещё раз.")
            return
        await message.reply_text(answer)
        chat.history = [*chat.history, question_message, {"role": "assistant", "content": answer}][-6:]
    finally:
        chat.waiting = False


async def show_ai_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        await query.answer("ИИ-подсказки пока недоступны. Используй подсказку в задаче.", show_alert=True)
        return
    if context.user_data.get("waiting_for_hint"):
        await query.answer("Подсказка уже готовится.")
        return

    context.user_data["waiting_for_hint"] = True
    try:
        await query.answer("Запрашиваю подсказку…")
        hint = await ask_groq(api_key, [
            {"role": "system", "content": HINT_PROMPT},
            {"role": "user", "content": HINT_REQUESTS[query.data]},
        ])
        if hint:
            subject = query.data.split(":", 1)[0]
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("Задать вопрос по подсказке", callback_data=f"ask:{subject}"),
            ]])
            await query.message.reply_text(f"{HINT_TITLE}\n\n{hint}", reply_markup=keyboard)
        else:
            await query.message.reply_text(
                "ИИ сейчас недоступен. Можно попробовать ещё раз или использовать подсказку в задаче."
            )
    finally:
        context.user_data.pop("waiting_for_hint", None)
