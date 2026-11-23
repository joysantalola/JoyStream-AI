"""Pruebas de regresión del Paso 25G.1."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch

from app import ai_comparisons_v2 as comparisons


MADRID = ZoneInfo("Europe/Madrid")


def make_session(stream_id, hour, minute, game, average, peak, day=22):
    started = datetime(2026, 11, day, hour, minute, tzinfo=MADRID)
    return {
        "stream_id": str(stream_id),
        "started_at": started.isoformat(),
        "_started_dt": started,
        "_average_num": float(average),
        "_peak_num": int(peak),
        "observed_minutes": 45.0,
        "games": [game],
    }


class TestPaso25G1(unittest.TestCase):
    def setUp(self):
        self.sessions = [
            make_session("rl-1", 12, 0, "Rocket League", 2.0, 4),
            make_session("rl-2", 14, 0, "Rocket League", 4.0, 6),
            make_session("peak-1", 15, 53, "PEAK", 2.84, 5),
        ]
        self.one_game_patch = patch.object(
            comparisons, "_one_game", side_effect=lambda session: session["games"][0]
        )
        self.one_game_patch.start()
        self.addCleanup(self.one_game_patch.stop)

    def test_three_emissions_two_rocket_league_one_peak(self):
        question = (
            "Compara mis tres directos de hoy, "
            "uno de Rocket League y otro de PEAK"
        )
        answer = comparisons._compare_same_day_game_switch(
            self.sessions,
            question,
            datetime(2026, 11, 22, 23, 0, tzinfo=MADRID),
        )
        self.assertIn("Comparación de 3 emisiones independientes", answer)
        self.assertEqual(answer.count("**Emisión "), 3)
        self.assertIn("**Rocket League**: 2 emisiones", answer)
        self.assertIn("**PEAK**: 1 emisión", answer)
        self.assertIn("media de las medias **3", answer)

    def test_does_not_duplicate_clock(self):
        answer = comparisons._compare_same_day_game_switch(
            self.sessions,
            "¿Cómo me fue al cambiar de juego?",
        )
        self.assertNotIn("15:53 h, 15:53 h", answer)
        self.assertIn("22/11/2026 a las 15:53 h", answer)

    def test_reports_shortfall_instead_of_comparing_two_of_three(self):
        question = "Compara mis tres directos de hoy, Rocket League y PEAK"
        answer = comparisons._compare_same_day_game_switch(
            self.sessions[:2],
            question,
            datetime(2026, 11, 22, 23, 0, tzinfo=MADRID),
        )
        self.assertIn("2 de 3 emisiones", answer)
        self.assertNotIn("Comparación de 2 emisiones independientes", answer)

    def test_today_excludes_previous_day(self):
        previous_day = make_session("old", 23, 0, "Fortnite", 8, 12, day=21)
        question = "Compara mis tres directos de hoy, Rocket League y PEAK"
        answer = comparisons._compare_same_day_game_switch(
            [previous_day] + self.sessions,
            question,
            datetime(2026, 11, 22, 23, 0, tzinfo=MADRID),
        )
        self.assertIn("Comparación de 3 emisiones independientes", answer)
        self.assertNotIn("Fortnite", answer)

    def test_explicit_game_switch_still_compares_last_pair(self):
        answer = comparisons._compare_same_day_game_switch(
            self.sessions,
            "¿Cómo me fue al cambiar de Rocket League a PEAK?",
        )
        self.assertIn("**Rocket League**", answer)
        self.assertIn("**PEAK**", answer)
        self.assertIn("Comparación de dos emisiones", answer)

    def test_count_parser(self):
        self.assertEqual(comparisons._requested_session_count("compara mis tres directos de hoy"), 3)
        self.assertEqual(comparisons._requested_session_count("compara 2 emisiones"), 2)
        self.assertIsNone(comparisons._requested_session_count("compara mis directos de hoy"))

    def test_classifier_routes_three_session_comparison(self):
        question = "Compara mis tres directos de hoy, uno de Rocket League y otro de PEAK"
        self.assertEqual(comparisons.classify_advanced_comparison(question), "game_switch")


if __name__ == "__main__":
    unittest.main()
