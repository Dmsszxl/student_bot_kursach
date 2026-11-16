from html import escape


TOPIC = "Ввод и вывод в C++"
TO_TOPIC = [("К теме", "io")]

EXAMPLE_CODE = """#include <iostream>

int main() {
    int number;
    std::cin >> number;
    std::cout << "Число: " << number << '\\n';
    return 0;
}"""

EXERCISE_CODE = """#include <iostream>

int main() {
    int a, b;
    std::cin >> a >> b;
    std::cout << b << ' ' << a << '\\n';
    return 0;
}"""

CPP_PAGES = {
    "menu": ("Программирование. Выбери тему.", [[(TOPIC, "io")]]),
    "io": (
        TOPIC,
        [
            [("Справка", "theory"), ("Пример", "example")],
            [("Решить задачу", "exercise")],
            [("Назад", "menu")],
        ],
    ),
    "theory": (
        "Ввод и вывод в C++\n\n"
        "Подключи библиотеку <code>&lt;iostream&gt;</code>.\n\n"
        "<code>std::cin &gt;&gt; x;</code> читает значение и записывает его в переменную x. "
        "Несколько целых чисел можно вводить через пробел или с новой строки.\n\n"
        "<code>std::cout &lt;&lt; x;</code> выводит значение x. "
        "При нескольких операциях вывода пробелы между значениями нужно указать явно. "
        "<code>'\\n'</code> переводит курсор на новую строку.",
        [TO_TOPIC],
    ),
    "example": (
        "Пример. Считать целое число и вывести его.\n\n"
        f"<pre>{escape(EXAMPLE_CODE)}</pre>\n"
        "Если ввести <code>7</code>, программа напечатает <code>Число: 7</code> "
        "и перейдёт на новую строку.",
        [TO_TOPIC],
    ),
    "exercise": (
        "Задача. Что напечатает программа, если ввести <code>4 9</code>?\n\n"
        f"<pre>{escape(EXERCISE_CODE)}</pre>",
        [[("4 9", "wrong"), ("9 4", "correct"), ("94", "wrong")], TO_TOPIC],
    ),
    "wrong": (
        "Пока неверно. Проверь, в каком порядке переменные идут после std::cout "
        "и какой символ программа печатает между ними.",
        [[("Объясни подробнее", "ai")], [("Попробовать ещё раз", "exercise")], TO_TOPIC],
    ),
    "correct": (
        "Верно! std::cin записывает 4 в a и 9 в b. "
        "std::cout выводит сначала b, потом пробел, затем a. Получается <code>9 4</code>.",
        [TO_TOPIC],
    ),
}
