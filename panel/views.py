from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from quiz.models import Package, Part, PartResult, Question, TelegramUser, TestSession
from quiz.services import session_result

from .forms import (
    PackageForm,
    PartForm,
    QuestionForm,
    ResultFilterForm,
    option_formset,
)

staff = staff_member_required(login_url="panel:login")


class LoginView(auth_views.LoginView):
    template_name = "panel/login.html"

    def dispatch(self, request, *args, **kwargs):
        # redirect_authenticated_user=True faqat is_authenticated'ni tekshiradi — agar
        # kirgan foydalanuvchi staff bo'lmasa, u /panel/ga (staff_member_required orqali)
        # va bu yerga cheksiz qaytariladi. Shuning uchun is_staff'ni ham tekshiramiz.
        if request.user.is_authenticated and request.user.is_staff:
            return redirect("panel:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        if not user.is_active or not user.is_staff:
            form.add_error(None, "Sizda admin panelga kirish huquqi yo'q.")
            return self.form_invalid(form)
        return super().form_valid(form)


# ------------------------------------------------------------ dashboard
@staff
def dashboard(request):
    finished = TestSession.objects.filter(status=TestSession.Status.FINISHED)
    today = timezone.localdate()
    week_ago = timezone.now() - timedelta(days=7)
    stats = {
        "users": TelegramUser.objects.count(),
        "finished": finished.count(),
        "in_progress": TestSession.objects.filter(status=TestSession.Status.IN_PROGRESS).count(),
        "today": finished.filter(finished_at__date=today).count(),
        "week": finished.filter(finished_at__gte=week_ago).count(),
        "avg": finished.aggregate(v=Avg("percentage"))["v"] or 0,
        "packages_active": Package.objects.filter(is_active=True).count(),
        "packages": Package.objects.count(),
        "questions": Question.objects.filter(is_active=True).count(),
    }
    part_rows = (
        PartResult.objects.filter(session__status=TestSession.Status.FINISHED)
        .values("part__title_en")
        .annotate(c=Sum("correct"), t=Sum("total"))
        .order_by("-t")[:8]
    )
    part_avgs = [
        (row["part__title_en"], round(row["c"] * 100 / row["t"], 1) if row["t"] else 0)
        for row in part_rows
    ]
    recent = finished.select_related("user", "package").order_by("-finished_at")[:8]
    return render(request, "panel/dashboard.html", {
        "stats": stats, "part_avgs": part_avgs, "recent": recent, "nav": "dashboard",
    })


# ------------------------------------------------------------- packages
@staff
def package_list(request):
    packages = Package.objects.annotate(
        part_count=Count("parts", distinct=True),
        q_count=Count("parts__questions", filter=Q(parts__questions__is_active=True), distinct=True),
        s_count=Count("sessions", distinct=True),
    )
    return render(request, "panel/package_list.html", {"packages": packages, "nav": "packages"})


@staff
def package_form(request, pk=None):
    package = get_object_or_404(Package, pk=pk) if pk else None
    form = PackageForm(request.POST or None, instance=package)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        if not package:
            messages.success(request, "Paket yaratildi. Endi bo'limlarni qo'shing.")
        else:
            messages.success(request, "Paket saqlandi.")
        return redirect("panel:package_detail", pk=obj.pk)
    return render(request, "panel/package_form.html", {"form": form, "package": package, "nav": "packages"})


@staff
def package_detail(request, pk):
    package = get_object_or_404(Package, pk=pk)
    parts = package.parts.annotate(
        q_count=Count("questions", filter=Q(questions__is_active=True)),
        q_all=Count("questions"),
    ).order_by("order", "id")
    return render(request, "panel/package_detail.html", {
        "package": package, "parts": parts, "nav": "packages",
    })


@staff
@require_POST
def package_toggle(request, pk):
    package = get_object_or_404(Package, pk=pk)
    package.is_active = not package.is_active
    package.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"«{package.name}» {'faollashtirildi' if package.is_active else 'o‘chirildi'}.")
    return redirect(request.POST.get("next") or "panel:package_list")


@staff
@require_POST
def package_delete(request, pk):
    package = get_object_or_404(Package, pk=pk)
    if package.sessions.exists():
        messages.error(request, "Bu paket bo'yicha natijalar bor — o'chirib bo'lmaydi. Uni nofaol qiling.")
        return redirect("panel:package_detail", pk=pk)
    package.delete()
    messages.success(request, "Paket o'chirildi.")
    return redirect("panel:package_list")


@staff
@require_POST
def package_duplicate(request, pk):
    src = get_object_or_404(Package, pk=pk)
    with transaction.atomic():
        name = f"{src.name} (nusxa)"
        n = 2
        while Package.objects.filter(name=name).exists():
            name = f"{src.name} (nusxa {n})"
            n += 1
        new = Package.objects.create(
            name=name, description=src.description, is_active=False,
            shuffle_questions=src.shuffle_questions,
        )
        for part in src.parts.all():
            questions = list(part.questions.prefetch_related("options"))
            part.pk = None
            part.package = new
            part.save()
            for q in questions:
                opts = list(q.options.all())
                q.pk = None
                q.part = part
                q.save()
                for o in opts:
                    o.pk = None
                    o.question = q
                    o.save()
    messages.success(request, f"Nusxa yaratildi: «{new.name}» (nofaol holatda).")
    return redirect("panel:package_detail", pk=new.pk)


# ---------------------------------------------------------------- parts
@staff
def part_form(request, package_pk=None, pk=None):
    part = get_object_or_404(Part, pk=pk) if pk else None
    package = part.package if part else get_object_or_404(Package, pk=package_pk)
    if part is None:
        next_order = (package.parts.order_by("-order").values_list("order", flat=True).first() or 0) + 1
        form = PartForm(request.POST or None, initial={"order": next_order})
    else:
        form = PartForm(request.POST or None, instance=part)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.package = package
        obj.save()
        messages.success(request, "Bo'lim saqlandi.")
        return redirect("panel:part_detail", pk=obj.pk)
    return render(request, "panel/part_form.html", {
        "form": form, "part": part, "package": package, "nav": "packages",
    })


@staff
def part_detail(request, pk):
    part = get_object_or_404(Part.objects.select_related("package"), pk=pk)
    questions = part.questions.prefetch_related("options").order_by("order", "id")
    return render(request, "panel/part_detail.html", {
        "part": part, "package": part.package, "questions": questions, "nav": "packages",
    })


@staff
@require_POST
def part_delete(request, pk):
    part = get_object_or_404(Part, pk=pk)
    package_pk = part.package_id
    if part.questions.filter(answers__isnull=False).exists():
        messages.error(request, "Bu bo'lim savollariga javoblar mavjud — o'chirib bo'lmaydi.")
        return redirect("panel:part_detail", pk=pk)
    part.delete()
    messages.success(request, "Bo'lim o'chirildi.")
    return redirect("panel:package_detail", pk=package_pk)


@staff
@require_POST
def part_move(request, pk, direction):
    part = get_object_or_404(Part, pk=pk)
    parts = list(part.package.parts.order_by("order", "id"))
    idx = parts.index(part)
    if direction == "up" and idx > 0:
        neighbor = parts[idx - 1]
    elif direction == "down" and idx < len(parts) - 1:
        neighbor = parts[idx + 1]
    else:
        neighbor = None
    if neighbor:
        part.order, neighbor.order = neighbor.order, part.order
        Part.objects.bulk_update([part, neighbor], ["order"])
    return redirect("panel:package_detail", pk=part.package_id)


# ------------------------------------------------------------ questions
@staff
def question_form(request, part_pk=None, pk=None):
    question = get_object_or_404(Question, pk=pk) if pk else None
    part = question.part if question else get_object_or_404(Part, pk=part_pk)
    FormSet = option_formset(extra=0 if question else 4)

    if question is None:
        next_order = (part.questions.order_by("-order").values_list("order", flat=True).first() or 0) + 1
        form = QuestionForm(request.POST or None, request.FILES or None, initial={"order": next_order})
    else:
        form = QuestionForm(request.POST or None, request.FILES or None, instance=question)
    formset = FormSet(request.POST or None, instance=question or Question(), prefix="opt")

    if request.method == "POST" and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            q = form.save(commit=False)
            q.part = part
            q.save()
            formset.instance = q
            formset.save()
        messages.success(request, "Savol saqlandi.")
        if "save_add" in request.POST:
            return redirect("panel:question_add", part_pk=part.pk)
        return redirect("panel:part_detail", pk=part.pk)

    return render(request, "panel/question_form.html", {
        "form": form, "formset": formset, "question": question, "part": part,
        "package": part.package, "nav": "packages",
    })


@staff
@require_POST
def question_delete(request, pk):
    q = get_object_or_404(Question, pk=pk)
    part_pk = q.part_id
    if q.answers.exists():
        q.is_active = False
        q.save(update_fields=["is_active"])
        messages.warning(request, "Savolga javoblar bor, shuning uchun u o'chirilmadi — nofaol qilindi.")
    else:
        q.delete()
        messages.success(request, "Savol o'chirildi.")
    return redirect("panel:part_detail", pk=part_pk)


# ---------------------------------------------------------------- users
@staff
def user_list(request):
    q = request.GET.get("q", "").strip()
    users = TelegramUser.objects.annotate(
        tests=Count("sessions", filter=Q(sessions__status=TestSession.Status.FINISHED)),
        best=Avg("sessions__percentage", filter=Q(sessions__status=TestSession.Status.FINISHED)),
    )
    if q:
        f = Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q) | Q(username__icontains=q)
        if q.isdigit():
            f |= Q(telegram_id=int(q))
        users = users.filter(f)
    page = Paginator(users.order_by("-created_at"), 30).get_page(request.GET.get("page"))
    return render(request, "panel/user_list.html", {"page": page, "q": q, "nav": "users"})


# -------------------------------------------------------------- results
def _filtered_sessions(request):
    form = ResultFilterForm(request.GET or None)
    qs = TestSession.objects.select_related("user", "package")
    if form.is_valid():
        d = form.cleaned_data
        if d.get("q"):
            q = d["q"].strip()
            f = (Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
                 | Q(user__phone__icontains=q) | Q(user__username__icontains=q))
            if q.isdigit():
                f |= Q(user__telegram_id=int(q))
            qs = qs.filter(f)
        if d.get("package"):
            qs = qs.filter(package=d["package"])
        if d.get("language"):
            qs = qs.filter(language=d["language"])
        if d.get("status"):
            qs = qs.filter(status=d["status"])
        if d.get("date_from"):
            qs = qs.filter(started_at__date__gte=d["date_from"])
        if d.get("date_to"):
            qs = qs.filter(started_at__date__lte=d["date_to"])
        if d.get("min_pct") is not None:
            qs = qs.filter(percentage__gte=d["min_pct"])
    sort = request.GET.get("sort", "-started_at")
    allowed = {"-started_at", "started_at", "-percentage", "percentage", "-finished_at"}
    qs = qs.order_by(sort if sort in allowed else "-started_at")
    return form, qs


@staff
def result_list(request):
    form, qs = _filtered_sessions(request)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "panel/result_list.html", {
        "form": form, "page": page, "nav": "results", "total": qs.count(),
        "querystring": params.urlencode(),
    })


@staff
def result_detail(request, pk):
    s = get_object_or_404(TestSession.objects.select_related("user", "package"), pk=pk)
    lang = s.language
    answers = {a.question_id: a for a in s.answers.select_related("selected_option")}
    questions = Question.objects.filter(pk__in=s.question_ids).select_related("part").prefetch_related("options")
    qmap = {q.id: q for q in questions}
    rows = []
    for idx, qid in enumerate(s.question_ids, start=1):
        q = qmap.get(qid)
        if not q:
            continue
        a = answers.get(qid)
        rows.append({
            "n": idx,
            "part_id": q.part_id,
            "part_title": q.part.title(lang),
            "text": q.text(lang),
            "options": [(o, o.text(lang)) for o in q.options.all()],
            "answer": a,
        })
    parts = session_result(s.id)["parts"]
    return render(request, "panel/result_detail.html", {
        "s": s, "rows": rows, "parts": parts, "nav": "results",
    })


@staff
@require_POST
def result_delete(request, pk):
    s = get_object_or_404(TestSession, pk=pk)
    s.delete()
    messages.success(request, "Natija o'chirildi. Foydalanuvchi testni qayta topshira oladi.")
    return redirect("panel:result_list")
