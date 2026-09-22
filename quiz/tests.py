from django.core.management import call_command
from django.test import TestCase

from . import services as S
from .models import TestSession


class FlowTests(TestCase):
    def setUp(self):
        call_command("seed_demo", verbosity=0)
        S.upsert_user(1, "u", first_name="Ali", last_name="Valiyev", phone="+998901112233")

    def test_full_flow_all_correct(self):
        s = S.start_session(1, "en")
        self.assertIsNotNone(s)
        parts_seen = []
        while (q := S.current_question(s.id)) is not None:
            if q.part_number not in parts_seen:
                parts_seen.append(q.part_number)
            correct = next(oid for oid, _, _ in q.options if self._is_correct(oid))
            self.assertEqual(S.submit_answer(999, s.id, q.question_id, correct), "stale")
            S.submit_answer(1, s.id, q.question_id, correct)
        s.refresh_from_db()
        self.assertEqual(parts_seen, [1, 2, 3])
        self.assertEqual(s.status, TestSession.Status.FINISHED)
        self.assertEqual(s.total_correct, s.total_questions)
        self.assertEqual(float(s.percentage), 100.0)
        self.assertEqual(
            list(s.part_results.order_by("part__order").values_list("total", flat=True)),
            [5, 5, 5],
        )

    def test_double_click_is_ignored(self):
        s = S.start_session(1, "ru")
        q = S.current_question(s.id)
        oid = q.options[0][0]
        self.assertEqual(S.submit_answer(1, s.id, q.question_id, oid), "ok")
        self.assertEqual(S.submit_answer(1, s.id, q.question_id, oid), "stale")
        self.assertEqual(s.answers.count(), 1)

    @staticmethod
    def _is_correct(oid):
        from .models import Option
        return Option.objects.get(pk=oid).is_correct
