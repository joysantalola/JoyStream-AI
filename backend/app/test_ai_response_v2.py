import unittest
from datetime import datetime, timezone, timedelta
from app.ai_response_v2 import precise_answer, readable_date, route


class TestAIResponse25E(unittest.TestCase):
    def setUp(self):
        self.context = {
            'community': {
                'followers_current': 279, 'followers_net_change': 15,
                'subscribers_current': 2, 'measurements': 22,
                'first_measurement': '2026-11-18T16:53:28+00:00',
                'last_measurement': '2026-11-22T13:04:48+00:00',
            },
            'live': {'recent_sessions': [{
                'stream_id': 'test', 'started_at': '2026-11-22T10:24:04+00:00',
                'peak_viewers': 10, 'average_viewers': 7.5,
                'min_viewers': 0, 'observed_minutes': 127.8, 'measurements': 6,
            }]}
        }
        start = datetime(2026, 11, 22, 10, tzinfo=timezone.utc)
        self.samples = [
            {'captured_at': start + timedelta(minutes=i*10), 'viewer_count': v}
            for i, v in enumerate([0, 3, 5, 7, 10, 10])
        ]

    def answer(self, question):
        return precise_answer(question, self.context, lambda _id: self.samples)

    def test_follower_synonyms(self):
        for q in ('¿Cuántos seguidores tengo?', '¿Cuánta gente me sigue?', 'Dime mis followers'):
            self.assertIn('279 seguidores', self.answer(q), q)

    def test_growth(self):
        ans = self.answer('¿Cómo ha evolucionado mi comunidad?')
        self.assertIn('+15', ans)
        self.assertIn('no el número bruto', ans)

    def test_subscribers(self):
        self.assertIn('2 suscriptores', self.answer('¿Cuántos suscriptores tengo?'))

    def test_peak_is_concise_and_late(self):
        ans = self.answer('¿Cuándo fue el pico de espectadores?')
        self.assertIn('11:40', ans)  # 10:40 UTC -> Madrid 11:40
        self.assertIn('2 mediciones', ans)
        self.assertNotIn('primera mitad', ans)

    def test_full_stream_and_halves(self):
        ans = self.answer('Analiza mi último directo')
        self.assertIn('**Último directo**', ans)
        self.assertIn('primera', ans)
        self.assertIn('segunda', ans)

    def test_recommendations_use_samples(self):
        ans = self.answer('¿Qué me recomiendas para mejorar mi último directo?')
        self.assertIsNotNone(ans)
        self.assertIn('próximos tres directos', ans)
        self.assertIn('Limitación', ans)

    def test_utc_converts_madrid_winter(self):
        self.assertIn('14:04', readable_date('2026-11-22T13:04:48+00:00'))

    def test_not_misroute_clips(self):
        self.assertIsNone(self.answer('¿Cuál es mi mejor clip?'))

    def test_missing_subscribers(self):
        self.context['community']['subscribers_current'] = None
        self.assertIn('No significa cero', self.answer('¿Cuántos suscriptores tengo?'))

    def test_historical_not_fabricated(self):
        self.assertIsNone(self.answer('¿Cuántos seguidores tenía ayer?'))


if __name__ == '__main__':
    unittest.main()
