from django.db import models
from django.utils import timezone


class Language(models.TextChoices):
    RU = "ru", "Русский"
    EN = "en", "English"


class Package(models.Model):
    name = models.CharField("Nomi", max_length=120, unique=True)
    description = models.TextField("Izoh", blank=True)
    is_active = models.BooleanField("Faol", default=True)
    shuffle_questions = models.BooleanField(
        "Part ichida savollarni aralashtirish", default=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Paket"
        verbose_name_plural = "Paketlar"

    def __str__(self):
        return self.name

    def question_count(self):
        return Question.objects.filter(part__package=self, is_active=True).count()


class Part(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name="parts")
    order = models.PositiveSmallIntegerField("Tartib", default=1)
    title_ru = models.CharField("Sarlavha (RU)", max_length=120)
    title_en = models.CharField("Sarlavha (EN)", max_length=120)
    instruction_ru = models.CharField("Ko'rsatma (RU)", max_length=255, blank=True)
    instruction_en = models.CharField("Ko'rsatma (EN)", max_length=255, blank=True)

    class Meta:
        ordering = ["package", "order", "id"]
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"

    def __str__(self):
        return f"{self.package.name} / {self.title_en}"

    def title(self, lang):
        return self.title_ru if lang == Language.RU else self.title_en

    def instruction(self, lang):
        return self.instruction_ru if lang == Language.RU else self.instruction_en


class Question(models.Model):
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField("Tartib", default=1)
    text_ru = models.TextField("Savol matni (RU)")
    text_en = models.TextField("Savol matni (EN)")
    image = models.ImageField("Rasm (ixtiyoriy)", upload_to="questions/", blank=True)
    is_active = models.BooleanField("Faol", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["part", "order", "id"]
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"

    def __str__(self):
        return self.text_ru[:60]

    def text(self, lang):
        return self.text_ru if lang == Language.RU else self.text_en

    @property
    def correct_option(self):
        return self.options.filter(is_correct=True).first()


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="options")
    order = models.PositiveSmallIntegerField("Tartib", default=1)
    text_ru = models.CharField("Variant (RU)", max_length=500)
    text_en = models.CharField("Variant (EN)", max_length=500)
    is_correct = models.BooleanField("To'g'ri javob", default=False)

    class Meta:
        ordering = ["question", "order", "id"]
        verbose_name = "Variant"
        verbose_name_plural = "Variantlar"

    def __str__(self):
        return self.text_ru

    def text(self, lang):
        return self.text_ru if lang == Language.RU else self.text_en


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField("Telegram ID", unique=True)
    username = models.CharField("Username", max_length=64, blank=True)
    first_name = models.CharField("Ism", max_length=100, blank=True)
    last_name = models.CharField("Familiya", max_length=100, blank=True)
    phone = models.CharField("Telefon", max_length=32, blank=True)
    language = models.CharField("Til", max_length=2, choices=Language.choices, blank=True)
    created_at = models.DateTimeField("Ro'yxatdan o'tgan", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Telegram foydalanuvchi"
        verbose_name_plural = "Telegram foydalanuvchilar"

    def __str__(self):
        return self.full_name or str(self.telegram_id)

    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name}".strip()


class TestSession(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "Jarayonda"
        FINISHED = "finished", "Yakunlangan"

    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="sessions")
    package = models.ForeignKey(Package, on_delete=models.PROTECT, related_name="sessions")
    language = models.CharField("Til", max_length=2, choices=Language.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.IN_PROGRESS)

    # Test boshlanganda savollar tartibi "muzlatiladi" — admin keyin savolni
    # o'zgartirsa ham, boshlangan test buzilmaydi.
    question_ids = models.JSONField(default=list)
    current_index = models.PositiveIntegerField(default=0)

    total_correct = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    started_at = models.DateTimeField("Boshlangan", default=timezone.now)
    finished_at = models.DateTimeField("Tugagan", null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Test natijasi"
        verbose_name_plural = "Test natijalari"
        indexes = [models.Index(fields=["status", "-started_at"])]

    def __str__(self):
        return f"{self.user} — {self.package} ({self.get_status_display()})"

    @property
    def is_finished(self):
        return self.status == self.Status.FINISHED

    @property
    def duration(self):
        if not self.finished_at:
            return None
        return self.finished_at - self.started_at

    @property
    def duration_display(self):
        d = self.duration
        if d is None:
            return "—"
        total = int(d.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    @property
    def wrong_count(self):
        return self.total_questions - self.total_correct

    @staticmethod
    def pct(correct, total):
        return round(correct * 100 / total, 1) if total else 0


class PartResult(models.Model):
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name="part_results")
    part = models.ForeignKey(Part, on_delete=models.CASCADE, related_name="results")
    correct = models.PositiveIntegerField(default=0)
    total = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["part__order", "part_id"]
        unique_together = [("session", "part")]
        verbose_name = "Bo'lim natijasi"
        verbose_name_plural = "Bo'lim natijalari"

    def __str__(self):
        return f"{self.session} / {self.part} — {self.correct}/{self.total}"

    @property
    def pct(self):
        return TestSession.pct(self.correct, self.total)


class Answer(models.Model):
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    selected_option = models.ForeignKey(Option, on_delete=models.SET_NULL, null=True)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["answered_at", "id"]
        unique_together = [("session", "question")]
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"
