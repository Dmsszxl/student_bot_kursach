import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # читает файл .env

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY"),
)

response = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[
        {"role": "system", "content": "Ты репетитор для первокурсников. Объясняй просто и коротко, на русском."},
        {"role": "user", "content": "Что такое производная? Объясни в трёх предложениях."},
    ],
)

print(response.choices[0].message.content)
print("Потрачено токенов:", response.usage.total_tokens)