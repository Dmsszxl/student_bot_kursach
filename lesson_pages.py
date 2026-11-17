from dataclasses import dataclass
from fractions import Fraction
from html import escape


Page = tuple[str, list[list[tuple[str, str]]]]


@dataclass(frozen=True)
class Exercise:
    question: str
    answer: str | int | Fraction
    hint: str
    explanation: str
    choices: tuple[str, ...] = ()
    code: str = ""


@dataclass(frozen=True)
class Lesson:
    title: str
    theory: str
    example: str
    exercises: tuple[Exercise, ...]
    example_code: str = ""


def topic_buttons(lessons: dict[str, Lesson]) -> list[list[tuple[str, str]]]:
    return [[(lesson.title, topic)] for topic, lesson in lessons.items()]


def add_lessons(
    pages: dict[str, Page], lessons: dict[str, Lesson], menu: str, *, html: bool = False
) -> dict[str, Exercise]:
    exercises = {}
    for topic, lesson in lessons.items():
        back = [("К теме", topic)]
        title = escape(lesson.title) if html else lesson.title
        theory = escape(lesson.theory) if html else lesson.theory
        example = escape(lesson.example) if html else lesson.example
        if lesson.example_code:
            example = f"<pre>{escape(lesson.example_code)}</pre>\n{example}"

        pages[topic] = (
            title,
            [
                [("Справка", f"{topic}-theory"), ("Пример", f"{topic}-example")],
                [("Решить задачу", f"{topic}-tasks")],
                [("Назад", menu)],
            ],
        )
        pages[f"{topic}-theory"] = (f"{title}\n\n{theory}", [back])
        pages[f"{topic}-example"] = (f"Пример. {title}\n\n{example}", [back])
        task_buttons = []

        for number, exercise in enumerate(lesson.exercises, start=1):
            exercise_id = f"{topic}-q{number}"
            exercises[exercise_id] = exercise
            task_buttons.append([(f"Задача {number}", exercise_id)])
            question = escape(exercise.question) if html else exercise.question
            hint = escape(exercise.hint) if html else exercise.hint
            explanation = escape(exercise.explanation) if html else exercise.explanation
            if exercise.code:
                question += f"\n\n<pre>{escape(exercise.code)}</pre>"
            if exercise.choices:
                answers = [
                    (choice, f"{exercise_id}-{'right' if choice == exercise.answer else 'wrong'}")
                    for choice in exercise.choices
                ]
            else:
                question += "\n\nОтправь число сообщением. Дробь можно записать как 3/4."
                answers = []

            task_back = [("К задачам", f"{topic}-tasks")]
            pages[exercise_id] = (
                f"Задача {number}. {title}\n\n{question}",
                [answers, task_back] if answers else [task_back],
            )
            pages[f"{exercise_id}-wrong"] = (
                f"Пока неверно. {hint}",
                [
                    [("Объясни подробнее", f"{exercise_id}-ai")],
                    [("Попробовать ещё раз", exercise_id)],
                    task_back,
                ],
            )
            pages[f"{exercise_id}-right"] = (f"Верно! {explanation}", [task_back, back])

        pages[f"{topic}-tasks"] = (f"{title}. Выбери задачу.", [*task_buttons, back])

    return exercises
