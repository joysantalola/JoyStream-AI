import unittest
from datetime import datetime, timedelta, timezone

from app.ai_comparisons import (
    answer_comparison, classify_comparison, save_recommendation_baseline,
)


class TestJoyStream25F(unittest.TestCase):
    def setUp(self):
        base = datetime(2026, 11, 1, 18, tzinfo=timezone.utc)
        self.sessions = [
            {"stream_id": "s1", "started_at": base.isoformat(), "average_viewers": 3.0,
             "peak_viewers": 6, "observed_minutes": 90, "games": ["Rocket League"]},
            {"stream_id": "s2", "started_at": (base + timedelta(days=2)).isoformat(), "average_viewers": 4.0,
             "peak_viewers": 8, "observed_minutes": 100, "games": ["Rocket League"]},
            {"stream_id": "s3", "started_at": (base + timedelta(days=4)).isoformat(), "average_viewers": 5.0,
             "peak_viewers": 9, "observed_minutes": 110, "games": ["Fortnite"]},
            {"stream_id": "s4", "started_at": (base + timedelta(days=6)).isoformat(), "average_viewers": 6.0,
             "peak_viewers": 11, "observed_minutes": 120, "games": ["Fortnite"]},
            {"stream_id": "s5", "started_at": (base + timedelta(days=8)).isoformat(), "average_viewers": 7.0,
             "peak_viewers": 12, "observed_minutes": 120, "games": ["Rocket League"]},
        ]
        self.context = {"live": {"recent_sessions": self.sessions, "games": []}}

    def fetch(self):
        return self.sessions

    def test_intent_latest_vs_previous(self):
        self.assertEqual(classify_comparison("¿Estoy mejorando respecto a mis últimos directos?"), "latest_vs_previous")

    def test_compare_latest_two(self):
        answer = answer_comparison("Compara mis dos últimos directos", self.context, self.fetch)
        self.assertIn("1 espectador más", answer)
        self.assertIn("no se puede atribuir", answer)

    def test_best_game_requires_repeated_sessions(self):
        answer = answer_comparison("¿Qué videojuego me funciona mejor?", self.context, self.fetch)
        self.assertIn("Fortnite", answer)
        self.assertIn("Rocket League", answer)
        self.assertIn("no demuestra", answer)

    def test_best_game_insufficient(self):
        context = {"live": {"recent_sessions": [self.sessions[0]], "games": []}}
        answer = answer_comparison("¿Qué juego da mejores resultados?", context, lambda: [self.sessions[0]])
        self.assertIn("no hay suficientes datos", answer.lower())

    def test_best_time_requires_multiple_slots(self):
        answer = answer_comparison("¿Qué horario me funciona mejor?", self.context, self.fetch)
        self.assertIsNotNone(answer)
        self.assertIn("franja", answer.lower())

    def test_best_time_insufficient(self):
        rows = self.sessions[:2]
        answer = answer_comparison("¿A qué hora me conviene hacer directos?", self.context, lambda: rows)
        self.assertIn("no hay suficientes directos", answer.lower())

    def test_recommendation_baseline_callback(self):
        saved = []
        ok = save_recommendation_baseline(
            self.context, "¿Qué me recomiendas?", "Prueba A", save_callback=lambda data: saved.append(data) or True
        )
        self.assertTrue(ok)
        self.assertEqual(saved[0]["baseline_stream_id"], "s5")
        self.assertEqual(saved[0]["baseline_average_viewers"], 7.0)

    def test_after_recommendation_without_baseline(self):
        answer = answer_comparison("¿He mejorado desde la última recomendación?", self.context,
                                   self.fetch, lambda: None)
        self.assertIn("no hay una recomendación guardada", answer.lower())

    def test_after_recommendation_no_later_stream(self):
        baseline = {"baseline_stream_id": "s5", "baseline_started_at": self.sessions[-1]["started_at"],
                    "baseline_average_viewers": 7.0, "baseline_games": "Rocket League"}
        answer = answer_comparison("¿He mejorado desde la última recomendación?", self.context,
                                   self.fetch, lambda: baseline)
        self.assertIn("todavía no hay un directo posterior", answer.lower())

    def test_after_recommendation_with_later_stream(self):
        later = dict(self.sessions[-1])
        later.update({"stream_id": "s6", "started_at": (datetime.fromisoformat(self.sessions[-1]["started_at"]) + timedelta(days=2)).isoformat(), "average_viewers": 8.5})
        rows = self.sessions + [later]
        baseline = {"baseline_stream_id": "s5", "baseline_started_at": self.sessions[-1]["started_at"],
                    "baseline_average_viewers": 7.0, "baseline_games": "Rocket League"}
        answer = answer_comparison("¿He mejorado desde la última recomendación?", self.context,
                                   lambda: rows, lambda: baseline)
        self.assertIn("subió", answer)
        self.assertIn("1,5 espectadores", answer)
        self.assertIn("no confirma", answer)

    def test_unrelated_question_not_intercepted(self):
        self.assertIsNone(answer_comparison("¿Qué clip debería publicar mañana?", self.context, self.fetch))

    def test_session_history_is_sorted(self):
        reversed_rows = list(reversed(self.sessions))
        answer = answer_comparison("Compara mis dos últimos directos", self.context, lambda: reversed_rows)
        self.assertIn("media **7** espectadores", answer)
        self.assertIn("media **6** espectadores", answer)


if __name__ == "__main__":
    unittest.main()
