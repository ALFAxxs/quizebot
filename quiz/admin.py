from django.contrib import admin

from .models import Answer, Option, Package, Part, PartResult, Question, TelegramUser, TestSession


class PartInline(admin.TabularInline):
    model = Part
    extra = 0


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "shuffle_questions", "created_at")
    list_filter = ("is_active",)
    inlines = [PartInline]


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "part", "order", "is_active")
    list_filter = ("part__package", "is_active")
    search_fields = ("text_ru", "text_en")
    inlines = [OptionInline]


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "telegram_id", "username", "language", "created_at")
    search_fields = ("first_name", "last_name", "phone", "telegram_id", "username")


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0
    readonly_fields = ("question", "selected_option", "is_correct", "answered_at")
    can_delete = False


class PartResultInline(admin.TabularInline):
    model = PartResult
    extra = 0
    readonly_fields = ("part", "correct", "total")
    can_delete = False


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user", "package", "language", "status", "total_correct", "total_questions",
        "percentage", "started_at", "finished_at",
    )
    list_filter = ("status", "language", "package")
    search_fields = ("user__first_name", "user__last_name", "user__phone")
    inlines = [PartResultInline, AnswerInline]
