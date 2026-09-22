"""
Test biznes-logikasi. Bu funksiyalar sinxron (Django ORM) — bot ularni
sync_to_async orqali chaqiradi, panel esa to'g'ridan-to'g'ri ishlatadi.
"""
import random
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    Answer,
    Option,
    Package,
    Part,
    PartResult,
    Question,
    TelegramUser,
    TestSession,
)

LETTERS = "ABCDEFGHIJ"


# ---------------------------------------------------------------- users
def upsert_user(telegram_id, username="", **fields):
    user, _ = TelegramUser.objects.get_or_create(telegram_id=telegram_id)
    user.username = username or user.username
    for k, v in fields.items():
        setattr(user, k, v)
    user.save()
    return user


def get_active_session(telegram_id):
    return (
        TestSession.objects.filter(
            user__telegram_id=telegram_id, status=TestSession.Status.IN_PROGRESS
        )
        .select_related("package", "user")
        .first()
    )


def get_last_finished_session(telegram_id):
    return (
        TestSession.objects.filter(
            user__telegram_id=telegram_id, status=TestSession.Status.FINISHED
        )
        .order_by("-finished_at")
        .first()
    )


# ------------------------------------------------------------- packages
def available_packages():
    """Faol, kamida bitta faol savoli bor paketlar."""
    return (
        Package.objects.filter(is_active=True)
        .annotate(qn=Count("parts__questions", filter=Q(parts__questions__is_active=True)))
        .filter(qn__gt=0)
    )


def build_question_order(package):
    ids = []
    for part in package.parts.order_by("order", "id"):
        q_ids = list(
            part.questions.filter(is_active=True)
            .annotate(oc=Count("options"), cc=Count("options", filter=Q(options__is_correct=True)))
            .filter(oc__gte=2, cc=1)
            .order_by("order", "id")
            .values_list("id", flat=True)
        )
        if package.shuffle_questions:
            random.shuffle(q_ids)
        ids.extend(q_ids)
    return ids


@transaction.atomic
def start_session(telegram_id, language):
    user = TelegramUser.objects.get(telegram_id=telegram_id)
    # Eski tugallanmagan testlar bo'lsa — ularni bekor qilmaymiz, shunchaki qaytaramiz
    existing = TestSession.objects.filter(user=user, status=TestSession.Status.IN_PROGRESS).first()
    if existing:
        return existing

    packages = list(available_packages())
    random.shuffle(packages)
    for package in packages:
        ids = build_question_order(package)
        if ids:
            return TestSession.objects.create(
                user=user,
                package=package,
                language=language,
                question_ids=ids,
                total_questions=len(ids),
            )
    return None


# ------------------------------------------------------------ questions
@dataclass
class QuestionPayload:
    session_id: int
    question_id: int
    index: int  # 1-based
    total: int
    part_number: int
    part_title: str
    part_instruction: str
    part_index: int  # part ichidagi savol raqami
    part_total: int
    is_first_in_part: bool
    text: str
    image_path: str = ""
    options: list = field(default_factory=list)  # [(option_id, letter, text)]


def current_question(session_id):
    session = TestSession.objects.select_related("package").get(pk=session_id)
    if session.status != TestSession.Status.IN_PROGRESS:
        return None
    if session.current_index >= len(session.question_ids):
        return None

    lang = session.language
    qid = session.question_ids[session.current_index]
    q = Question.objects.select_related("part").prefetch_related("options").filter(pk=qid).first()
    if q is None:
        # Savol o'chirilgan bo'lsa — o'tkazib yuboramiz
        session.question_ids = [i for i in session.question_ids if i != qid]
        session.total_questions = len(session.question_ids)
        session.save(update_fields=["question_ids", "total_questions"])
        return current_question(session_id)

    qpart = dict(
        Question.objects.filter(pk__in=session.question_ids).values_list("id", "part_id")
    )
    seq_parts = []
    for i in session.question_ids:
        pid = qpart.get(i)
        if pid and pid not in seq_parts:
            seq_parts.append(pid)
    part_number = seq_parts.index(q.part_id) + 1
    in_part = [i for i in session.question_ids if qpart.get(i) == q.part_id]
    part_index = in_part.index(q.id) + 1

    options = [
        (o.id, LETTERS[i], o.text(lang)) for i, o in enumerate(q.options.all()[: len(LETTERS)])
    ]
    return QuestionPayload(
        session_id=session.id,
        question_id=q.id,
        index=session.current_index + 1,
        total=len(session.question_ids),
        part_number=part_number,
        part_title=q.part.title(lang),
        part_instruction=q.part.instruction(lang),
        part_index=part_index,
        part_total=len(in_part),
        is_first_in_part=part_index == 1,
        text=q.text(lang),
        image_path=q.image.path if q.image else "",
        options=options,
    )


class SubmitResult:
    OK = "ok"
    FINISHED = "finished"
    STALE = "stale"  # eski/takroriy bosish
    INVALID = "invalid"


@transaction.atomic
def submit_answer(telegram_id, session_id, question_id, option_id):
    session = (
        TestSession.objects.select_for_update()
        .filter(pk=session_id, user__telegram_id=telegram_id)
        .first()
    )
    if session is None or session.status != TestSession.Status.IN_PROGRESS:
        return SubmitResult.STALE
    if session.current_index >= len(session.question_ids):
        return SubmitResult.STALE
    if session.question_ids[session.current_index] != question_id:
        return SubmitResult.STALE

    option = Option.objects.filter(pk=option_id, question_id=question_id).first()
    if option is None:
        return SubmitResult.INVALID

    Answer.objects.get_or_create(
        session=session,
        question_id=question_id,
        defaults={
            "selected_option": option,
            "is_correct": option.is_correct,
        },
    )
    session.current_index += 1
    if session.current_index >= len(session.question_ids):
        _finalize(session)
        return SubmitResult.FINISHED
    session.save(update_fields=["current_index"])
    return SubmitResult.OK


def _finalize(session):
    qpart = dict(
        Question.objects.filter(pk__in=session.question_ids).values_list("id", "part_id")
    )
    totals = {}
    for pid in qpart.values():
        totals[pid] = totals.get(pid, 0) + 1
    correct = {}
    for qid, ok in session.answers.values_list("question_id", "is_correct"):
        if ok:
            pid = qpart.get(qid)
            if pid:
                correct[pid] = correct.get(pid, 0) + 1

    PartResult.objects.bulk_create([
        PartResult(session=session, part_id=pid, correct=correct.get(pid, 0), total=total)
        for pid, total in totals.items()
    ])

    session.total_questions = sum(totals.values())
    session.total_correct = sum(correct.values())
    session.percentage = (
        round(session.total_correct * 100 / session.total_questions, 2)
        if session.total_questions
        else 0
    )
    session.status = TestSession.Status.FINISHED
    session.finished_at = timezone.now()
    session.save()


# -------------------------------------------------------------- results
def session_result(session_id):
    s = TestSession.objects.get(pk=session_id)
    lang = s.language
    parts = []
    for pr in s.part_results.select_related("part").order_by("part__order", "part_id"):
        parts.append(
            {
                "part_id": pr.part_id,
                "title": pr.part.title(lang),
                "correct": pr.correct,
                "total": pr.total,
                "wrong": pr.total - pr.correct,
                "pct": pr.pct,
            }
        )
    return {
        "language": lang,
        "parts": parts,
        "correct": s.total_correct,
        "wrong": s.total_questions - s.total_correct,
        "total": s.total_questions,
        "pct": float(s.percentage),
        "duration": s.duration_display,
    }


def session_part_titles(session_id):
    s = TestSession.objects.get(pk=session_id)
    qpart = dict(Question.objects.filter(pk__in=s.question_ids).values_list("id", "part_id"))
    seen = []
    for i in s.question_ids:
        pid = qpart.get(i)
        if pid and pid not in seen:
            seen.append(pid)
    parts = {p.id: p for p in Part.objects.filter(pk__in=seen)}
    return [f"Part {n} — {parts[pid].title(s.language)}" for n, pid in enumerate(seen, start=1)]
