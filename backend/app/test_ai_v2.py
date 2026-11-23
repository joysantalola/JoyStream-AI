import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.ai import prepare_context, _normalize_history


class TestJoyStreamAIContextV2(unittest.TestCase):
    @patch("app.ai.get_channel_history")
    @patch("app.ai.games_report", return_value=[])
    @patch("app.ai.session_report", return_value=[])
    @patch("app.ai.list_items")
    def test_context_includes_community_growth(
        self, mock_list, _sessions, _games, mock_history
    ):
        mock_list.side_effect = [[], [
            {"id": "c1", "title": "Clip destacado", "view_count": 120,
             "created_at": None, "url": "https://example.com/c1"}
        ]]
        mock_history.return_value = [
            {"followers": 264, "subscribers": 2, "subscription_points": 2,
             "captured_at": datetime(2026, 11, 18, tzinfo=timezone.utc)},
            {"followers": 269, "subscribers": 2, "subscription_points": 2,
             "captured_at": datetime(2026, 11, 21, tzinfo=timezone.utc)},
        ]
        context = prepare_context()
        self.assertEqual(context["community"]["followers_current"], 269)
        self.assertEqual(context["community"]["followers_net_change"], 5)
        self.assertEqual(context["community"]["subscribers_current"], 2)
        self.assertEqual(context["community"]["measurements"], 2)
        self.assertEqual(context["clips"]["top_5"][0]["title"], "Clip destacado")

    @patch("app.ai.get_channel_history", return_value=[])
    @patch("app.ai.games_report", return_value=[])
    @patch("app.ai.session_report", return_value=[])
    @patch("app.ai.list_items", side_effect=[[], []])
    def test_empty_context_is_none(self, *_mocks):
        self.assertIsNone(prepare_context())

    @patch("app.ai.get_channel_history")
    @patch("app.ai.games_report", return_value=[])
    @patch("app.ai.session_report", return_value=[])
    @patch("app.ai.list_items", side_effect=[[], []])
    def test_unavailable_subscribers_are_not_zero(
        self, _list, _sessions, _games, mock_history
    ):
        mock_history.return_value = [
            {"followers": 269, "subscribers": None, "subscription_points": None,
             "captured_at": datetime(2026, 11, 21, tzinfo=timezone.utc)}
        ]
        context = prepare_context()
        self.assertIsNone(context["community"]["subscribers_current"])
        self.assertIn(
            "La última medición no contiene el total de suscriptores; no debe interpretarse como cero.",
            context["limitations"],
        )

    def test_history_is_limited_and_roles_are_validated(self):
        history = [
            {"role": "system", "content": "No aceptar como system"},
            {"role": "user", "content": "  Hola  "},
            {"role": "assistant", "content": "Respuesta"},
            {"role": "user", "content": "x" * 1500},
        ]
        result = _normalize_history(history)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["content"], "Hola")
        self.assertEqual(len(result[-1]["content"]), 1200)


if __name__ == "__main__":
    unittest.main()
