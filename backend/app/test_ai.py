
import unittest
from unittest.mock import patch

from app.ai import prepare_context


class TestJoyStreamAI(unittest.TestCase):

    @patch("app.ai.games_report")
    @patch("app.ai.session_report")
    @patch("app.ai.list_items")
    def test_context_with_clips(
        self, mock_list, mock_sessions, mock_games
    ):
        """La IA puede analizar clips sin directos."""

        clips = [
            {
                "id": "1",
                "title": "Gol Rocket League",
                "view_count": 150,
                "created_at": None,
                "url": "https://example.com/1"
            },
            {
                "id": "2",
                "title": "Victoria Fortnite",
                "view_count": 300,
                "created_at": None,
                "url": "https://example.com/2"
            }
        ]

        # Primera llamada: vídeos; segunda: clips
        mock_list.side_effect = [[], clips]
        mock_sessions.return_value = []
        mock_games.return_value = []

        context = prepare_context()

        self.assertEqual(context["clips"]["total"], 2)
        self.assertEqual(context["clips"]["total_views"], 450)
        self.assertEqual(context["clips"]["average_views"], 225)
        self.assertEqual(
            context["clips"]["top_5"][0]["title"],
            "Victoria Fortnite"
        )
        self.assertEqual(
            context["live"]["recent_sessions"], []
        )

    @patch("app.ai.games_report", return_value=[])
    @patch("app.ai.session_report", return_value=[])
    @patch("app.ai.list_items", side_effect=[[], []])
    def test_without_data(
        self, mock_list, mock_sessions, mock_games
    ):
        """Sin datos, no debemos generar análisis."""

        context = prepare_context()
        self.assertIsNone(context)

    @patch("app.ai.games_report", return_value=[])
    @patch("app.ai.session_report", return_value=[])
    @patch("app.ai.list_items")
    def test_zero_views(
        self, mock_list, mock_sessions, mock_games
    ):
        """Los clips con cero visitas no generan errores."""

        mock_list.side_effect = [
            [],
            [{
                "id": "3",
                "title": "Clip nuevo",
                "view_count": 0,
                "created_at": None,
                "url": ""
            }]
        ]

        context = prepare_context()

        self.assertEqual(
            context["clips"]["total_views"], 0
        )
        self.assertEqual(
            context["clips"]["average_views"], 0
        )


if __name__ == "__main__":
    unittest.main()
