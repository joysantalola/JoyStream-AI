"""Pruebas Paso 25G.2 — estadísticas ponderadas y validaciones."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from app import ai_comparisons_v2 as mod

MADRID = ZoneInfo("Europe/Madrid")

def session(sid, h, game, avg, peak, n=None):
    time = datetime(2026, 11, 22, h, 0, tzinfo=MADRID)
    return {"stream_id": sid, "started_at": time.isoformat(),
            "_started_dt": time, "_average_num": avg, "_peak_num": peak,
            "observed_minutes": 60, "measurements": n, "games": [game]}

class TestPaso25G2(unittest.TestCase):
    def setUp(self):
        self.rows = [session("r1", 11, "Rocket League", 7.5, 10, 140),
                     session("r2", 14, "Rocket League", 1.86, 4, 40),
                     session("p1", 15, "PEAK", 2.84, 5, 73)]
        p = patch.object(mod, "_one_game", side_effect=lambda s: s["games"][0])
        p.start()
        self.addCleanup(p.stop)

    def test_three_sessions(self):
        ans = mod._compare_multiple_sessions(self.rows, datetime(2026,11,22,tzinfo=MADRID).date())
        self.assertEqual(ans.count("**Emisión "), 3)
    def test_measurements_display(self):
        ans = mod._compare_multiple_sessions(self.rows, None)
        self.assertIn("140 muestras", ans)
        self.assertIn("73 muestras", ans)
    def test_average_of_averages(self):
        ans = mod._compare_multiple_sessions(self.rows, None)
        self.assertIn("media de las medias **4,68**", ans)
    def test_weighted_mean(self):
        ans = mod._compare_multiple_sessions(self.rows, None)
        self.assertIn("**6,25**", ans)  # (7.5*140 + 1.86*40)/180 = 6.24666
    def test_percent(self):
        self.assertEqual(mod._percent_change(4.68,2.84), "-39,3 %")
    def test_zero_reference(self):
        self.assertIn("no calculable", mod._percent_change(0,2.84))
    def test_missing_samples_no_weighting(self):
        rows = [dict(s) for s in self.rows]
        rows[1]["measurements"] = None
        self.assertIn("media ponderada no disponible", mod._compare_multiple_sessions(rows,None))
    def test_invalid_zero_samples(self):
        self.assertIsNone(mod._measurements({"measurements":0}))
    def test_strict_category_eligibility(self):
        ans = mod._compare_games_strict(self.rows)
        self.assertIn("no hay suficientes datos", ans)
    def test_strict_category_weighting(self):
        more = self.rows + [session("p2", 16, "PEAK", 4, 6, 50)]
        ans = mod._compare_games_strict(more)
        self.assertIn("ponderada por muestras", ans)
    def test_sample_count(self):
        self.assertEqual(mod._weighted_average(self.rows[:2])[1],180)
    def test_no_duplicate_clocks(self):
        ans = mod._compare_multiple_sessions(self.rows, None)
        self.assertNotIn("11:00 h, 11:00 h",ans)
    def test_game_switch_unchanged(self):
        ans = mod._compare_same_day_game_switch(self.rows, "¿Cómo me fue al cambiar de juego?")
        self.assertIn("Comparación de dos emisiones", ans)
    def test_percent_positive(self):
        self.assertEqual(mod._percent_change(2,3),"+50 %")

if __name__ == "__main__":
    unittest.main()
