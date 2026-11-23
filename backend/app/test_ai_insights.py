import unittest
from datetime import datetime, timedelta, timezone

from app.ai_insights import classify, answer_fact, audience_insights


class JoyAISemanticsTest(unittest.TestCase):
    def setUp(self):
        self.t0 = datetime(2026, 11, 21, 10, tzinfo=timezone.utc)
        self.context = {
            'community': {
                'followers_current': 272,
                'followers_net_change': 8,
                'subscribers_current': 2,
                'first_measurement': '2026-11-18T10:00:00+00:00',
                'last_measurement': '2026-11-21T12:43:48+00:00',
                'measurements': 13,
            },
            'live': {'recent_sessions': [{
                'stream_id': 'abc', 'started_at': self.t0.isoformat(),
                'average_viewers': 4.49, 'peak_viewers': 10,
                'min_viewers': 0, 'observed_minutes': 86.5,
                'measurements': 6,
            }]},
        }

    def test_followers_synonyms(self):
        phrases = ['¿Cuántos seguidores tengo?', 'Dime mis followers',
                   '¿Cuánta gente me sigue?', 'Seguidores actuales', 'Seguidores']
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(classify(phrase), 'followers_current')
                self.assertIn('272 seguidores', answer_fact(phrase, self.context))

    def test_followers_net_is_not_gross(self):
        for phrase in ['¿Cuántos seguidores he ganado?', '¿Cómo ha evolucionado mi comunidad?', 'Crecimiento de seguidores']:
            with self.subTest(phrase=phrase):
                self.assertEqual(classify(phrase), 'followers_growth')
                result = answer_fact(phrase, self.context)
                self.assertIn('+8 seguidores', result)
                self.assertIn('no equivale', result)

    def test_historical_range_not_as_current(self):
        answer = answer_fact('¿Cuántos followers tenía la semana pasada?', self.context)
        self.assertIn('No puedo dar una cifra histórica', answer)

    def test_subscribers_missing_distinct_from_zero(self):
        self.context['community']['subscribers_current'] = None
        answer = answer_fact('¿Cuántos suscriptores tengo?', self.context)
        self.assertIn('no significa cero', answer)

    def test_peak_timing_from_samples(self):
        values = [1, 2, 3, 5, 9, 10]
        samples = [{'captured_at': self.t0 + timedelta(minutes=10 * i), 'viewer_count': val}
                   for i, val in enumerate(values)]
        result = audience_insights(samples)
        self.assertEqual(result['peak'], '10')
        self.assertEqual(result['peak_first_at'], (self.t0 + timedelta(minutes=50)).isoformat())
        self.assertGreater(result['second_half_mean'], result['first_half_mean'])
        msg = answer_fact('Analiza mi último directo', self.context, lambda _id: samples)
        self.assertIn(result['peak_first_at'], msg)
        self.assertIn('no implica crecimiento constante', msg)

    def test_nonrelated_question_goes_to_llm(self):
        self.assertIsNone(classify('¿Qué clips debería publicar mañana?'))
        self.assertIsNone(classify('¿Por qué tengo pocos seguidores?'))

    def test_empty_samples_safe(self):
        self.assertIsNone(audience_insights([]))
        answer = answer_fact('Analiza mi último directo', self.context, lambda _: [])
        self.assertIn('No hay muestras temporales válidas', answer)

    def test_one_measurement_no_growth(self):
        self.context['community']['measurements'] = 1
        self.assertIn('No hay dos mediciones', answer_fact('Variación de seguidores', self.context))


if __name__ == '__main__':
    unittest.main()
