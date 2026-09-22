"""
"ВСТУПИТЕЛЬНОЕ ТЕСТИРОВАНИЕ" — ru.pdf va eng.pdf fayllaridan olingan haqiqiy kirish
testi (25 savol: Math 10, English 10, IQ 5). Manba PDF'lardagi "List otvetov"
bo'sh edi — to'g'ri javoblar har bir savol yechilib aniqlandi.

Eslatma: eng.pdf faylida IQ bo'limi (21-25) inglizchaga tarjima qilinmay, o'zbek
tilida qolib ketgan (manba faylning o'zidagi kamchilik). Shu sabab EN matnlar
uchun bu 5 ta savol shu yerda inglizchaga tarjima qilib yozildi — mazmuni va
javoblari xuddi ru.pdf bilan bir xil.

Ishlatish:  python manage.py seed_entrance_test            (mavjud bo'lsa o'tkazib yuboradi)
            python manage.py seed_entrance_test --reset    (qayta yaratadi)
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from quiz.models import Option, Package, Part, Question

PACKAGE_NAME = "Вступительное тестирование"

INSTR = {
    "math": ("Выберите правильный ответ.", "Choose the correct answer."),
    "english": ("Выберите вариант, который лучше всего подходит.", "Choose the option that fits best."),
    "iq": ("Найдите закономерность и выберите ответ.", "Find the pattern and choose the answer."),
}


def o(ru, en, ok=False):
    return (ru, en, ok)


MATH = [
    ("Каждый день Роберт съедает 40% оставшихся в его банке фисташек. К концу второго дня "
     "остаётся 27 фисташек. Сколько фисташек было в банке в начале первого дня?",
     "Each day, Robert eats 40% of the pistachios remaining in his jar. At the end of the "
     "second day, 27 pistachios remain. How many pistachios were in the jar at the start of "
     "the first day?",
     [o("75", "75", True), o("80", "80"), o("85", "85"), o("95", "95")]),

    ("За две недели Джон съел 20 фунтов куриных крылышек и 15 фунтов хот-догов. Кайл съел на "
     "20% больше куриных крылышек и на 40% больше хот-догов, чем Джон. Учитывая только "
     "крылышки и хот-доги, на сколько процентов больше еды по весу съел Кайл, чем Джон "
     "(приблизительно)?",
     "Over a two-week period, John ate 20 pounds of chicken wings and 15 pounds of hot dogs. "
     "Kyle ate 20% more chicken wings and 40% more hot dogs than John. Considering only "
     "chicken wings and hot dogs, Kyle ate approximately what percentage more food, by "
     "weight, than John?",
     [o("25%", "25%"), o("27%", "27%"), o("29%", "29%", True), o("30%", "30%")]),

    ("Цена книги со скидкой на 20% ниже розничной цены. Джеймс покупает книгу с дополнительной "
     "скидкой 30% от цены со скидкой на специальной распродаже. Какой процент от розничной "
     "цены заплатил Джеймс?",
     "The discount price of a book is 20% less than its retail price. James purchases the "
     "book at an additional 30% discount on the discount price at a special book sale. What "
     "percentage of the retail price did James pay?",
     [o("42%", "42%"), o("48%", "48%"), o("50%", "50%"), o("56%", "56%", True)]),

    ("Джоан купила куклу со скидкой 10% от первоначальной цены в $105,82. Однако ей пришлось "
     "заплатить налог с продаж в размере x% от цены со скидкой. Если общая сумма, которую "
     "заплатила Джоан за куклу, составила $100, чему равно значение x?",
     "Joanne bought a doll at a 10% discount off the original price of $105.82. However, she "
     "had to pay a sales tax of x% on the discounted price. If the total amount Joanne paid "
     "for the doll was $100, what is the value of x?",
     [o("2", "2"), o("3", "3"), o("4", "4"), o("5", "5", True)]),

    ("У Джули квадратный забор, окружающий её сад. Она решает расширить сад, увеличив каждую "
     "сторону забора на 10%. На сколько процентов увеличится площадь сада Джули после этого "
     "расширения?",
     "Julie has a square fence that encloses her garden. She decides to expand her garden by "
     "making each side of the fence 10% longer. After this expansion, by what percent will "
     "the area of Julie's garden increase?",
     [o("20%", "20%"), o("21%", "21%", True), o("22%", "22%"), o("25%", "25%")]),

    ("Генри проехал 150 миль со скоростью 30 миль в час, а затем ещё 200 миль со скоростью 50 "
     "миль в час. Какова была его средняя скорость (в милях в час) за всю поездку, с "
     "точностью до сотых?",
     "Henry drives 150 miles at 30 miles per hour and then another 200 miles at 50 miles per "
     "hour. What was his average speed, in miles per hour, for the entire journey, to the "
     "nearest hundredth?",
     [o("38,89", "38.89", True), o("40,00", "40.00"), o("42,33", "42.33"), o("43,58", "43.58")]),

    ("Пекарня раздавала купоны в честь открытия. Каждый купон стоил либо $1, либо $3, либо $5. "
     "Купонов по $1 было выдано в два раза больше, чем купонов по $3, а купонов по $3 — в три "
     "раза больше, чем купонов по $5. Общая стоимость всех выданных купонов составила $360. "
     "Сколько купонов по $3 было выдано?",
     "A bakery gave out coupons to celebrate its grand opening. Each coupon was worth either "
     "$1, $3, or $5. Twice as many $1 coupons were given out as $3 coupons, and three times "
     "as many $3 coupons were given out as $5 coupons. The total value of all the coupons "
     "given out was $360. How many $3 coupons were given out?",
     [o("40", "40"), o("45", "45"), o("48", "48"), o("54", "54", True)]),

    ("Алекс, Боб и Карл коллекционируют ракушки. У Боба вдвое меньше ракушек, чем у Карла. У "
     "Алекса втрое больше ракушек, чем у Боба. Если у Алекса и Боба вместе 60 ракушек, сколько "
     "ракушек у Карла?",
     "Alex, Bob, and Carl all collect seashells. Bob has half as many seashells as Carl. Alex "
     "has three times as many seashells as Bob. If Alex and Bob together have 60 seashells, "
     "how many seashells does Carl have?",
     [o("15", "15"), o("20", "20"), o("30", "30", True), o("40", "40")]),

    ("Стоимость междугороднего телефонного звонка определяется фиксированной платой за первые "
     "5 минут и фиксированной платой за каждую дополнительную минуту. Если 15-минутный звонок "
     "стоит $3,50, а 20-минутный звонок стоит $4,75, сколько будет стоить 40-минутный звонок "
     "(в долларах)?",
     "The cost of a long-distance telephone call is determined by a basic fixed charge for "
     "the first 5 minutes and a fixed charge for each additional minute. If a 15-minute call "
     "costs $3.50 and a 20-minute call costs $4.75, what is the total cost, in dollars, of a "
     "40-minute call?",
     [o("$8,25", "$8.25"), o("$9,50", "$9.50"), o("$9,75", "$9.75", True), o("$10,25", "$10.25")]),

    ("Группа рабочих может собрать весь виноград с 10 квадратных метров виноградника за 20 "
     "минут. При такой скорости, сколько минут понадобится группе, чтобы собрать весь виноград "
     "с 300 квадратных метров этого виноградника?",
     "A group of workers can harvest all the grapes from 10 square meters of a vineyard in 20 "
     "minutes. At this rate, how many minutes will the group need to harvest all the grapes "
     "from 300 square meters of this vineyard?",
     [o("60", "60"), o("200", "200"), o("400", "400"), o("600", "600", True)]),
]

# English bo'limi savollari ataylab tarjima qilinmagan — tilni tekshiradi.
ENGLISH = [
    ("The director was highly _____ with the excellent results of the students in the final exam.",
     [o("confused", "confused"), o("disappointed", "disappointed"), o("exhausted", "exhausted"),
      o("impressed", "impressed", True)]),

    ("The company managed to make a huge _____ this year despite the economic crisis.",
     [o("profit", "profit", True), o("value", "value"), o("debt", "debt"), o("loss", "loss")]),

    ("If the company _____ the price of the product, more people would buy it.",
     [o("lowered", "lowered", True), o("had lowered", "had lowered"), o("lowers", "lowers"),
      o("will lower", "will lower")]),

    ("Please ensure you meet the _____ for submitting your application. Late forms will not be accepted.",
     [o("border", "border"), o("deadline", "deadline", True), o("limit", "limit"), o("timeline", "timeline")]),

    ("The financial reports _____ by the accounting team every Friday afternoon.",
     [o("are prepared", "are prepared", True), o("prepares", "prepares"), o("are preparing", "are preparing"),
      o("prepared", "prepared")]),

    ("If you have any questions regarding the course, please do not hesitate to _____ our support team.",
     [o("connect", "connect"), o("contact", "contact", True), o("touch", "touch"), o("relate", "relate")]),

    ("By the time we arrive at the office, the presentation _____.",
     [o("will finish", "will finish"), o("will have finished", "will have finished", True),
      o("finishes", "finishes"), o("is finishing", "is finishing")]),

    ("The receptionist asked me where _____.",
     [o("the meeting was", "the meeting was", True), o("the meeting is", "the meeting is"),
      o("was the meeting", "was the meeting"), o("is the meeting", "is the meeting")]),

    ("I _____ for this company since 2022, and I really enjoy my job.",
     [o("work", "work"), o("worked", "worked"), o("am working", "am working"),
      o("have been working", "have been working", True)]),

    ("You _____ wear a formal suit to the classes, but it is highly recommended.",
     [o("don't have to", "don't have to", True), o("mustn't", "mustn't"), o("shouldn't", "shouldn't"),
      o("can't", "can't")]),
]

IQ = [
    ("Стороны треугольника равны 6, 10 и 11. Чему равна одна из сторон равностороннего "
     "треугольника с таким же периметром?",
     "A triangle has sides equal to 6, 10, and 11. What is the length of one side of an "
     "equilateral triangle with the same perimeter?",
     [o("10", "10"), o("11", "11"), o("6", "6"), o("9", "9", True)]),

    ("2, 4, 9, 11, 16, 18, ...? Найдите удвоенное значение следующего числа в этой "
     "последовательности.",
     "2, 4, 9, 11, 16, 18, ...? Find double the value of the next number in this sequence.",
     [o("40", "40"), o("23", "23"), o("20", "20"), o("46", "46", True)]),

    ("На ферме 30 коров и некоторое количество кур. Общее число куриных ног равно общему числу "
     "коровьих ног. Сколько всего животных на ферме?",
     "A farm has 30 cows and some chickens. The total number of chicken legs equals the total "
     "number of cow legs. How many animals are there on the farm in total?",
     [o("60", "60"), o("100", "100"), o("120", "120"), o("90", "90", True)]),

    ("Сутки на планете Фикрлаб длиннее земных суток на 40 минут. На сколько отличается неделя "
     "на Фикрлабе от земной недели?",
     "A day on planet Fikrlab is 40 minutes longer than a day on Earth. By how much does a "
     "week on Fikrlab differ from a week on Earth?",
     [o("7 часов 20 минут", "7 hours 20 minutes"), o("4 часа 40 минут", "4 hours 40 minutes", True),
      o("40 минут", "40 minutes"), o("2 часа 20 минут", "2 hours 20 minutes")]),

    ("Один человек сказал: «Я прожил 44 года, 44 месяца, 44 недели, 44 дня и 44 часа». Сколько "
     "ему лет?",
     "A person said: \"I have lived 44 years, 44 months, 44 weeks, 44 days, and 44 hours.\" "
     "How old is he?",
     [o("46 лет", "46 years old"), o("48 лет", "48 years old", True), o("49 лет", "49 years old"),
      o("47 лет", "47 years old")]),
]


class Command(BaseCommand):
    help = "PDF'dan olingan haqiqiy kirish testini (Math/English/IQ) bazaga qo'shadi"

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Mavjud bo'lsa o'chirib qayta yaratish")

    @transaction.atomic
    def handle(self, *args, reset=False, **kw):
        existing = Package.objects.filter(name=PACKAGE_NAME).first()
        if existing:
            if not reset:
                self.stdout.write(f"«{PACKAGE_NAME}» mavjud — o'tkazib yuborildi")
                return
            if existing.sessions.exists():
                self.stdout.write(self.style.WARNING(
                    f"«{PACKAGE_NAME}» bo'yicha natijalar bor — o'chirilmadi"
                ))
                return
            existing.delete()

        pkg = Package.objects.create(
            name=PACKAGE_NAME,
            description="ru.pdf / eng.pdf asosidagi haqiqiy kirish testi (25 savol).",
            is_active=True,
        )

        math_part = Part.objects.create(
            package=pkg, order=1,
            title_ru="Математика", title_en="Mathematics",
            instruction_ru=INSTR["math"][0], instruction_en=INSTR["math"][1],
        )
        for qn, (ru, en, opts) in enumerate(MATH, start=1):
            q = Question.objects.create(part=math_part, order=qn, text_ru=ru, text_en=en)
            for on, (oru, oen, ok) in enumerate(opts, start=1):
                Option.objects.create(question=q, order=on, text_ru=oru, text_en=oen, is_correct=ok)

        eng_part = Part.objects.create(
            package=pkg, order=2,
            title_ru="Английский язык", title_en="English",
            instruction_ru=INSTR["english"][0], instruction_en=INSTR["english"][1],
        )
        for qn, (text, opts) in enumerate(ENGLISH, start=1):
            q = Question.objects.create(part=eng_part, order=qn, text_ru=text, text_en=text)
            for on, (oru, oen, ok) in enumerate(opts, start=1):
                Option.objects.create(question=q, order=on, text_ru=oru, text_en=oen, is_correct=ok)

        iq_part = Part.objects.create(
            package=pkg, order=3,
            title_ru="IQ / Логическое мышление", title_en="IQ / Logical Reasoning",
            instruction_ru=INSTR["iq"][0], instruction_en=INSTR["iq"][1],
        )
        for qn, (ru, en, opts) in enumerate(IQ, start=1):
            q = Question.objects.create(part=iq_part, order=qn, text_ru=ru, text_en=en)
            for on, (oru, oen, ok) in enumerate(opts, start=1):
                Option.objects.create(question=q, order=on, text_ru=oru, text_en=oen, is_correct=ok)

        self.stdout.write(self.style.SUCCESS(f"«{PACKAGE_NAME}» yaratildi (25 savol)."))
