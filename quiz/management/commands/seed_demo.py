"""
Demo ma'lumotlar: 2 ta paket, har birida Math / English / IQ bo'limlari.
Ishlatish:  python manage.py seed_demo            (mavjud bo'lsa o'tkazib yuboradi)
            python manage.py seed_demo --reset    (demo paketlarni qayta yaratadi)
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import Option, Package, Part, Question


def o(ru, en=None, ok=False):
    return (ru, en if en is not None else ru, ok)


TITLES = {
    "math": ("Математика", "Mathematics"),
    "english": ("Английский язык", "English"),
    "iq": ("IQ / Логическое мышление", "IQ / Logical Reasoning"),
}
INSTR = {
    "math": ("Выберите правильный ответ.", "Choose the correct answer."),
    "english": ("Выберите вариант, который лучше всего подходит.", "Choose the option that fits best."),
    "iq": ("Найдите закономерность и выберите ответ.", "Find the pattern and choose the answer."),
}

DATA = {
    "Package 1": {
        "math": [
            ("Чему равно 15% от 240?", "What is 15% of 240?", [o("32"), o("36", ok=True), o("40"), o("24")]),
            ("Решите уравнение: 3x − 7 = 20", "Solve: 3x − 7 = 20", [o("x = 7"), o("x = 8"), o("x = 9", ok=True), o("x = 11")]),
            ("Площадь прямоугольника 6 × 9 см равна…", "The area of a 6 × 9 cm rectangle is…",
             [o("54 см²", "54 cm²", True), o("30 см²", "30 cm²"), o("45 см²", "45 cm²"), o("60 см²", "60 cm²")]),
            ("Среднее арифметическое чисел 4, 8, 12, 16?", "The mean of 4, 8, 12, 16 is?", [o("8"), o("10", ok=True), o("12"), o("11")]),
            ("Товар стоил 200 000 сум, цена выросла на 10%. Новая цена?",
             "An item cost 200,000 sum and the price rose by 10%. The new price?",
             [o("210 000"), o("220 000", "220,000", True), o("202 000", "202,000"), o("240 000", "240,000")]),
        ],
        "english": [
            ("She ___ to school every day.", "She ___ to school every day.", [o("go"), o("goes", ok=True), o("going"), o("gone")]),
            ("Choose the synonym of «big».", "Choose the synonym of «big».", [o("tiny"), o("large", ok=True), o("thin"), o("short")]),
            ("I have lived here ___ 2019.", "I have lived here ___ 2019.", [o("for"), o("since", ok=True), o("from"), o("at")]),
            ("If it rains tomorrow, we ___ at home.", "If it rains tomorrow, we ___ at home.", [o("stay"), o("stayed"), o("will stay", ok=True), o("would stayed")]),
            ("Choose the correct plural of «child».", "Choose the correct plural of «child».", [o("childs"), o("childes"), o("children", ok=True), o("childrens")]),
        ],
        "iq": [
            ("Продолжите ряд: 2, 4, 8, 16, …", "Continue the series: 2, 4, 8, 16, …", [o("24"), o("30"), o("32", ok=True), o("20")]),
            ("Какое слово лишнее?", "Which word is the odd one out?",
             [o("Яблоко", "Apple"), o("Банан", "Banana"), o("Морковь", "Carrot", True), o("Груша", "Pear")]),
            ("Если все A — это B, и все B — это C, то все A — это…", "If all A are B and all B are C, then all A are…",
             [o("C", ok=True), o("не C", "not C"), o("только B", "only B"), o("нельзя определить", "cannot be determined")]),
            ("Продолжите ряд: 1, 1, 2, 3, 5, 8, …", "Continue the series: 1, 1, 2, 3, 5, 8, …", [o("11"), o("12"), o("13", ok=True), o("14")]),
            ("Часы показывают 3:00. Какой угол между стрелками?", "A clock shows 3:00. What is the angle between the hands?",
             [o("45°"), o("90°", ok=True), o("120°"), o("180°")]),
        ],
    },
    "Package 2": {
        "math": [
            ("Чему равно 7² − 3²?", "What is 7² − 3²?", [o("16"), o("40", ok=True), o("42"), o("58")]),
            ("Упростите: 2(a + 3) − a", "Simplify: 2(a + 3) − a", [o("a + 6", ok=True), o("a + 3"), o("3a + 6"), o("a − 6")]),
            ("Поезд проехал 180 км за 2 часа. Его скорость?", "A train travels 180 km in 2 hours. Its speed?",
             [o("80 км/ч", "80 km/h"), o("90 км/ч", "90 km/h", True), o("100 км/ч", "100 km/h"), o("360 км/ч", "360 km/h")]),
            ("Сколько будет 3/4 + 1/8?", "What is 3/4 + 1/8?", [o("4/12"), o("7/8", ok=True), o("5/8"), o("1")]),
            ("Периметр квадрата 36 см. Его сторона?", "A square has a perimeter of 36 cm. Its side?",
             [o("6 см", "6 cm"), o("9 см", "9 cm", True), o("12 см", "12 cm"), o("18 см", "18 cm")]),
        ],
        "english": [
            ("They ___ football when it started to rain.", "They ___ football when it started to rain.",
             [o("play"), o("were playing", ok=True), o("have played"), o("are playing")]),
            ("Choose the antonym of «ancient».", "Choose the antonym of «ancient».", [o("old"), o("modern", ok=True), o("historic"), o("rare")]),
            ("This is ___ best book I have ever read.", "This is ___ best book I have ever read.", [o("a"), o("an"), o("the", ok=True), o("—")]),
            ("He is interested ___ history.", "He is interested ___ history.", [o("on"), o("at"), o("in", ok=True), o("about")]),
            ("The letter ___ yesterday.", "The letter ___ yesterday.", [o("was sent", ok=True), o("is sent"), o("sent"), o("has been send")]),
        ],
        "iq": [
            ("Продолжите ряд: 3, 6, 11, 18, 27, …", "Continue the series: 3, 6, 11, 18, 27, …", [o("36"), o("38", ok=True), o("40"), o("35")]),
            ("Рука относится к перчатке, как нога к…", "Hand is to glove as foot is to…",
             [o("колену", "knee"), o("носку", "sock", True), o("пальцу", "toe"), o("шагу", "step")]),
            ("Какое число лишнее: 2, 3, 5, 9, 11?", "Which number is the odd one out: 2, 3, 5, 9, 11?", [o("2"), o("5"), o("9", ok=True), o("11")]),
            ("Али выше Бобура, Бобур выше Сардора. Кто самый низкий?",
             "Ali is taller than Bobur, Bobur is taller than Sardor. Who is the shortest?",
             [o("Али", "Ali"), o("Бобур", "Bobur"), o("Сардор", "Sardor", True), o("Нельзя определить", "Cannot be determined")]),
            ("Продолжите ряд букв: A, C, E, G, …", "Continue the letter series: A, C, E, G, …", [o("H"), o("I", ok=True), o("J"), o("K")]),
        ],
    },
}


class Command(BaseCommand):
    help = "Demo test paketlarini yaratadi"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Demo paketlarni o'chirib qayta yaratish")

    @transaction.atomic
    def handle(self, *args, reset=False, **kw):
        for pkg_name, parts in DATA.items():
            existing = Package.objects.filter(name=pkg_name).first()
            if existing:
                if not reset:
                    self.stdout.write(f"«{pkg_name}» mavjud — o'tkazib yuborildi")
                    continue
                if existing.sessions.exists():
                    self.stdout.write(self.style.WARNING(f"«{pkg_name}» bo'yicha natijalar bor — o'chirilmadi"))
                    continue
                existing.delete()
            pkg = Package.objects.create(name=pkg_name, description="Demo paket", is_active=True)
            for order, (cat, questions) in enumerate(parts.items(), start=1):
                part = Part.objects.create(
                    package=pkg, order=order,
                    title_ru=TITLES[cat][0], title_en=TITLES[cat][1],
                    instruction_ru=INSTR[cat][0], instruction_en=INSTR[cat][1],
                )
                for qn, (ru, en, opts) in enumerate(questions, start=1):
                    q = Question.objects.create(part=part, order=qn, text_ru=ru, text_en=en)
                    for on, (oru, oen, ok) in enumerate(opts, start=1):
                        Option.objects.create(question=q, order=on, text_ru=oru, text_en=oen, is_correct=ok)
            self.stdout.write(self.style.SUCCESS(f"«{pkg_name}» yaratildi"))
