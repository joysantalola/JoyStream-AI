import unittest
from datetime import datetime, timedelta, timezone

from app.ai_comparisons_v2 import (
    answer_advanced_comparison,
    classify_advanced_comparison,
)


class TestJoyStream25G(unittest.TestCase):
    def setUp(self):
        # Horarios locales de Madrid durante noviembre (UTC+1).
        base = datetime(2026, 11, 22, 14, 9, tzinfo=timezone.utc)
        self.sessions = [
            {
                "stream_id": "rl-1",
                "started_at": base.isoformat(),
                "average_viewers": 1.86,
                "peak_viewers": 4,
                "observed_minutes": 40,
                "games": ["Rocket League"],
            },
            {
                "stream_id": "peak-1",
                "started_at": (base + timedelta(minutes=44)).isoformat(),
                "average_viewers": 2.84,
                "peak_viewers": 5,
                "observed_minutes": 66.8,
                "games": ["PEAK"],
            },
            {
                "stream_id": "rl-2",
                "started_at": (base + timedelta(days=1)).isoformat(),
                "average_viewers": 2.5,
                "peak_viewers": 6,
                "observed_minutes": 80,
                "games": ["Rocket League"],
            },
            {
                "stream_id": "peak-2",
                "started_at": (base + timedelta(days=2)).isoformat(),
                "average_viewers": 3.2,
                "peak_viewers": 7,
                "observed_minutes": 90,
                "games": ["PEAK"],
            },
            {
                "stream_id": "mixed",
                "started_at": (base + timedelta(days=3)).isoformat(),
                "average_viewers": 9.0,
                "peak_viewers": 12,
                "observed_minutes": 90,
                "games": ["Rocket League", "PEAK"],
            },
        ]
        self.context = {"live": {"recent_sessions": self.sessions}}

    def fetch(self):
        return self.sessions

    def test_classifies_game_switch(self):
        self.assertEqual(
            classify_advanced_comparison("¿Cómo me fue al cambiar de juego?"),
            "game_switch",
        )

    def test_compares_same_day_independent_streams(self):
        answer = answer_advanced_comparison(
            "¿Cómo me fue al cambiar de juego?", self.context, self.fetch
        )
        self.assertIn("emisiones independientes", answer)
        self.assertIn("Rocket League", answer)
        self.assertIn("PEAK", answer)
        self.assertIn("1,86", answer)
        self.assertIn("2,84", answer)
        self.assertIn("52,7", answer)
        self.assertIn("no demuestra", answer)

    def test_ignores_same_game_pair(self):
        rows = [self.sessions[0], dict(self.sessions[0], stream_id="rl-3",
                started_at=(datetime.fromisoformat(self.sessions[0]["started_at"]) +
                            timedelta(minutes=20)).isoformat())]
        answer = answer_advanced_comparison(
            "¿Cómo me fue al cambiar de juego?",
            {"live": {"recent_sessions": rows}},
            lambda: rows,
        )
        self.assertIn("no encuentro dos emisiones independientes", answer.lower())

    def test_classifies_named_game_switch(self):
        self.assertEqual(
            classify_advanced_comparison("¿Cómo me fue al cambiar de Rocket League a PEAK?"),
            "game_switch",
        )

    def test_does_not_pair_different_local_days(self):
        a = dict(self.sessions[0])
        b = dict(self.sessions[1])
        b["started_at"] = (datetime.fromisoformat(a["started_at"]) +
                           timedelta(hours=10)).isoformat()
        answer = answer_advanced_comparison(
            "¿Cómo me fue al cambiar de juego?",
            {"live": {"recent_sessions": [a, b]}},
            lambda: [a, b],
        )
        self.assertIn("no encuentro dos emisiones independientes", answer.lower())

    def test_latest_qualifying_pair_is_used(self):
        rows = self.sessions[:2]
        later = [
            dict(rows[0], stream_id="rl-later",
                 started_at=(datetime.fromisoformat(rows[0]["started_at"]) +
                             timedelta(days=4)).isoformat()),
            dict(rows[1], stream_id="peak-later",
                 started_at=(datetime.fromisoformat(rows[1]["started_at"]) +
                             timedelta(days=4, minutes=30)).isoformat(),
                 average_viewers=4.0),
        ]
        all_rows = rows + later
        answer = answer_advanced_comparison(
            "¿Cómo me fue al cambiar de juego?",
            {"live": {"recent_sessions": all_rows}},
            lambda: all_rows,
        )
        self.assertIn("4 espectadores", answer)

    def test_classifies_same_day_two_stream_comparison(self):
        self.assertEqual(
            classify_advanced_comparison(
                "Compara mis dos directos de hoy, uno de Rocket League y otro de PEAK"
            ),
            "game_switch",
        )

    def test_classifies_best_weekday(self):
        self.assertEqual(
            classify_advanced_comparison("¿Qué día de la semana me funciona mejor?"),
            "best_weekday",
        )

    def test_weekday_comparison(self):
        # 2 sesiones lunes y 2 martes en hora local de Madrid.
        monday = datetime(2026, 11, 23, 17, tzinfo=timezone.utc)
        rows = [
            {"stream_id": "m1", "started_at": monday.isoformat(),
             "average_viewers": 3, "games": ["PEAK"]},
            {"stream_id": "m2", "started_at": (monday + timedelta(days=7)).isoformat(),
             "average_viewers": 5, "games": ["PEAK"]},
            {"stream_id": "t1", "started_at": (monday + timedelta(days=1)).isoformat(),
             "average_viewers": 6, "games": ["PEAK"]},
            {"stream_id": "t2", "started_at": (monday + timedelta(days=8)).isoformat(),
             "average_viewers": 8, "games": ["PEAK"]},
        ]
        answer = answer_advanced_comparison(
            "¿Qué día de la semana me funciona mejor?",
            {"live": {"recent_sessions": rows}},
            lambda: rows,
        )
        self.assertIn("Lunes", answer)
        self.assertIn("Martes", answer)
        self.assertIn("martes", answer.split("mayor media observada es")[-1])

    def test_weekday_requires_two_days_with_two_sessions(self):
        rows = self.sessions[:2]
        answer = answer_advanced_comparison(
            "¿Qué día de la semana me funciona mejor?",
            {"live": {"recent_sessions": rows}},
            lambda: rows,
        )
        self.assertIn("no hay suficientes directos", answer.lower())

    def test_game_comparison_excludes_mixed_sessions(self):
        rows = self.sessions
        answer = answer_advanced_comparison(
            "¿Qué videojuego me funciona mejor?",
            {"live": {"recent_sessions": rows}},
            lambda: rows,
        )
        self.assertIn("sesiones con categoría única", answer)
        self.assertIn("Se excluyeron 1 emisiones", answer)
        self.assertNotIn("media de medias por directo **9**", answer)

    def test_game_comparison_explains_insufficient_samples(self):
        rows = self.sessions[:2]
        answer = answer_advanced_comparison(
            "¿Qué videojuego me funciona mejor?",
            {"live": {"recent_sessions": rows}},
            lambda: rows,
        )
        self.assertIn("no hay suficientes datos", answer.lower())

    def test_unrelated_question_not_intercepted(self):
        self.assertIsNone(
            answer_advanced_comparison(
                "¿Qué clip debería publicar mañana?", self.context, self.fetch
            )
        )

    def test_same_day_uses_madrid_timezone(self):
        # 23:30 UTC del 22/11 y 00:10 UTC del 23/11 son mismo día local?
        # En noviembre Madrid UTC+1: 00:30 y 01:10 del 23/11.
        a = dict(self.sessions[0], started_at="2026-11-22T23:30:00+00:00")
        b = dict(self.sessions[1], stream_id="peak-next-utc",
                 started_at="2026-11-23T00:10:00+00:00")
        answer = answer_advanced_comparison(
            "¿Cómo me fue al cambiar de juego?",
            {"live": {"recent_sessions": [a, b]}},
            lambda: [a, b],
        )
        self.assertIn("emisiones independientes", answer)


if __name__ == "__main__":
    unittest.main()
