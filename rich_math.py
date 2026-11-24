import re
from html import escape

from telegram.error import BadRequest, EndPointNotFound


# Groq иногда меняет разделители или оставляет отдельную формулу без них.
MATH_PART = re.compile(
    r"(?P<code>```[\s\S]*?```|`[^`\n]+`)"
    r"|\\\[(?P<display>[\s\S]+?)\\\]"
    r"|\$\$(?P<display_dollars>[\s\S]+?)\$\$"
    r"|\\\((?P<inline>[^\n]+?)\\\)"
    r"|(?<![\\$])\$(?![\s$])(?P<inline_dollar>[^$\n]+?)(?<!\s)\$(?!\$)"
    r"|(?P<standalone>^[ \t]*\\(?:lim|frac|dfrac|sqrt|sum|int|begin)(?![a-zA-Z])[^\n]*"
    r"(?:\n[ \t]*(?:\\[a-zA-Z]+|=)[^\n]*)*)",
    re.MULTILINE,
)

PLAIN_COMMANDS = {
    "to": "→", "rightarrow": "→", "infty": "∞", "approx": "≈", "neq": "≠",
    "cdot": "·", "times": "×", "le": "≤", "ge": "≥", "pi": "π",
    "left": "", "right": "", "displaystyle": "",
}


def plain_formula(latex: str) -> str:
    latex = re.sub(r"\\overset\{\\text\{[^{}]*\}\}\{=\}", " = ", latex)
    latex = re.sub(r"\\(?:d|t)?frac\s*([0-9])([0-9])", r"(\1)/(\2)", latex)
    latex = re.sub(r"\\sqrt\s*\{([^{}]*)\}", r"√(\1)", latex)
    latex = re.sub(r"\\(?:d|t)?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}", r"(\1)/(\2)", latex)
    latex = re.sub(r"\\(?:begin|end)\{[^{}]+\}", "", latex)
    latex = latex.replace(r"\\", " / ").replace("&", " ")
    latex = re.sub(r"\\([a-zA-Z]+)", lambda match: PLAIN_COMMANDS.get(match[1], match[1]), latex)
    latex = re.sub(r"lim_\{([^{}]*)\}", r"lim (\1) ", latex)
    return latex.replace("{", "(").replace("}", ")")


def ai_math_html(text: str) -> str:
    matches = list(MATH_PART.finditer(text))
    if not any(match.lastgroup != "code" for match in matches):
        return ""

    html = []
    position = 0
    for match in matches:
        html.append(escape(text[position:match.start()]).replace("\n", "<br>"))
        kind = match.lastgroup
        content = match[kind]
        if kind == "code":
            if content.startswith("```"):
                _, _, code = content[3:-3].partition("\n")
                html.append(f"<pre>{escape(code or content[3:-3])}</pre>")
            else:
                html.append(f"<code>{escape(content[1:-1])}</code>")
        elif kind in ("inline", "inline_dollar"):
            html.append(f"<tg-math>{escape(content.strip())}</tg-math>")
        else:
            latex = " ".join(line.strip() for line in content.splitlines())
            html.append(f"<tg-math-block>{escape(latex)}</tg-math-block>")
        position = match.end()
    html.append(escape(text[position:]).replace("\n", "<br>"))
    return "".join(html)


def ai_math_plain(text: str) -> str:
    def replace(match):
        if match.lastgroup == "code":
            return match[0]
        return plain_formula(match[match.lastgroup].strip())

    return MATH_PART.sub(replace, text)


async def send_math(message, html, *, keyboard=None, edit=False):
    """Use Telegram's rich format when available. Return None on rejection."""
    data = {"chat_id": message.chat_id, "rich_message": {"html": html}}
    if keyboard is not None:
        data["reply_markup"] = keyboard
    method = "sendRichMessage"
    if edit:
        data["message_id"] = message.message_id
        method = "editMessageText"
    elif message.is_topic_message:
        data["message_thread_id"] = message.message_thread_id
    try:
        return await message.get_bot().do_api_request(method, data)
    except BadRequest as error:
        if edit and "message is not modified" in str(error).lower():
            return True
        return None
    except EndPointNotFound:
        return None
