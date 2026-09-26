#!/usr/bin/env python3
"""Behavior checks using explicitly synthetic trips; optionally export a demo."""

import argparse
import json
import tempfile
import unittest
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from subprocess import run
import sys

from render_report import prepare, render


def demo_trip(days=2, travelers=2, rooms=1):
    source = {'url': 'https://example.org/', 'label': 'Fonte fittizia: solo collaudo', 'checked_on': '2026-09-05'}
    alternatives = []
    for index, name in enumerate(('Economica · demo', 'Comfort · demo')):
        places = []
        for ident, kind, label, coords in [('hotel', 'hotel', 'Alloggio dimostrativo', [44.41, 8.93]), ('food', 'restaurant', 'Ristorante dimostrativo', [44.408, 8.932]), ('visit', 'attraction', 'Visita dimostrativa', [44.412, 8.936])]:
            places.append({'id': ident, 'kind': kind, 'name': label, 'address': 'Posizione illustrativa, non una struttura reale', 'description': 'Contenuto sintetico per verificare il report. Non usare per prenotare o pianificare un viaggio reale.', 'why': 'Mostra il collegamento tra programma, scheda e mappa.', 'url': 'https://example.org/', 'sources': [source], 'coordinates': coords, 'coordinate_source': 'https://example.org/'})
        costs = []

        def cost(day, category, label, place_id, unit, quantity, low, high, basis='estimate'):
            costs.append({'day': day, 'category': category, 'label': label, 'place_id': place_id, 'unit': unit, 'quantity': str(quantity), 'unit_min': str(low), 'unit_max': str(high), 'basis': basis, 'note': 'Valore sintetico per collaudo; non è un prezzo di mercato.', 'sources': []})

        cost(1, 'viaggio', 'Viaggio A/R condiviso', None, 'gruppo', 1, 100, 120)
        schedule = []
        for day in range(1, days + 1):
            cost(day, 'pasti', 'Pasti della giornata (demo)', 'food', 'persona / giorno', travelers, 30, 40)
            cost(day, 'visite', 'Ingresso dimostrativo', 'visit', 'persona', travelers, 5, 5)
            if day < days:
                cost(day, 'alloggi', 'Camera per una notte', 'hotel', 'camera / notte', rooms, 100 * (index + 1), 120 * (index + 1))
            cost(day, 'pasti', 'Colazione inclusa (demo)', 'hotel', 'persona', travelers, 0, 0, 'included')
            schedule.append({'day': day, 'title': 'Una giornata di esempio', 'overnight': 'hotel' if day < days else None, 'notes': 'Programma fittizio. Ultimo giorno: rientro. In caso di pioggia sostituire la visita, senza sommare i costi.', 'events': [
                {'time': '09:00–10:00', 'title': 'Trasferimento illustrativo', 'details': 'Durata dimostrativa: verificare su un viaggio reale.', 'place_id': None},
                {'time': '10:00–12:00', 'title': 'Visita di esempio', 'details': 'Visita e pausa; contenuto di collaudo.', 'place_id': 'visit'},
                {'time': '12:30–14:00', 'title': 'Pasto di esempio', 'details': 'Spesa collegata alla scheda del locale.', 'place_id': 'food'},
            ]})
        alternatives.append({'id': str(index), 'name': name, 'base': 'Liguria · dati sintetici', 'reason': 'Alternativa di collaudo per confrontare i costi.', 'tradeoffs': 'Nessuna ricerca di strutture reali effettuata in questo esempio.', 'warnings': [], 'places': places, 'schedule': schedule, 'costs': costs})
    return {'title': 'Una pausa in Liguria · DEMO', 'region': 'Liguria (esempio)', 'origin': 'Partenza dimostrativa', 'period': 'Periodo illustrativo, date da scegliere', 'travelers': travelers, 'days': days, 'currency': 'EUR', 'transport': 'Auto condivisa (esempio)' if travelers > 2 else 'Mezzi pubblici (esempio)', 'party': 'Amici' if travelers > 2 else 'Coppia', 'interests': 'Borghi, cucina, passeggiate', 'room_setup': f'{rooms} camere condivise', 'dates_confirmed': False, 'researched_on': '2026-09-05', 'budget': {'amount': '5000', 'scope': 'group'}, 'reserve_percent': '10', 'assumptions': ['Dati interamente sintetici; nessuna disponibilità verificata.'], 'warnings': ['DEMO TECNICA: luoghi, coordinate e prezzi illustrativi. Non è un itinerario ricercato.'], 'recommended': '0', 'alternatives': alternatives}


class ReportTests(unittest.TestCase):
    def test_shared_room_meals_and_person_budget(self):
        trip = demo_trip()
        trip['budget'] = {'amount': '297', 'scope': 'person'}
        options, cap, _, _ = prepare(trip)
        self.assertEqual(cap, Decimal('594'))
        self.assertEqual((options[0]['low'], options[0]['high'], options[0]['contingency'], options[0]['total']), tuple(map(Decimal, ('340', '420', '42', '462'))))
        self.assertEqual(options[0]['categories']['alloggi'], [Decimal('100'), Decimal('120')])
        self.assertEqual(sum(v[1] for v in options[0]['daily'].values()), Decimal('420'))
        self.assertEqual(options[1]['total'], Decimal('594'))
        trip['budget']['amount'] = '296.99'
        with self.assertRaisesRegex(ValueError, 'oltre tetto'):
            prepare(trip)

    def test_four_days_friends_three_nights(self):
        options, _, _, _ = prepare(demo_trip(4, 4, 2))
        cheap = options[0]
        self.assertEqual(cheap['categories']['alloggi'], [Decimal('600'), Decimal('720')])
        self.assertEqual(cheap['total'], Decimal('1716'))
        self.assertEqual(sum(day['overnight'] is not None for day in cheap['schedule']), 3)

    def test_reject_bad_inputs(self):
        for field, value in [('unit_min', '-1'), ('quantity', '0'), ('unit_max', 'NaN'), ('unit_max', 'Infinity'), ('place_id', 'missing'), ('day', 3), ('basis', 'invented')]:
            with self.subTest(field=field, value=value):
                trip = demo_trip()
                trip['alternatives'][0]['costs'][0][field] = value
                with self.assertRaises(ValueError):
                    prepare(trip)
        trip = demo_trip()
        trip['alternatives'][0]['costs'][0]['basis'] = 'published_for_dates'
        with self.assertRaisesRegex(ValueError, 'fonte'):
            prepare(trip)
        trip = demo_trip()
        trip['alternatives'][0]['schedule'][1]['day'] = 1
        with self.assertRaisesRegex(ValueError, 'ogni giorno'):
            prepare(trip)

    def test_partial_research_and_no_feasible_options(self):
        trip = demo_trip()
        place = trip['alternatives'][0]['places'][0]
        place.update(coordinates=None, coordinate_note='Fonte cartografica non disponibile')
        output = render(trip)
        self.assertIn('Report preliminare', output)
        self.assertIn('Posizione non verificata', output)
        trip.update(alternatives=[], fewer_options_reason='Nessuna soluzione nel tetto. Mancano almeno 100 EUR; valutare una notte in meno.')
        self.assertIn('Nessuna soluzione nel tetto', render(trip))
        trip.pop('fewer_options_reason')
        with self.assertRaisesRegex(ValueError, 'meno di due'):
            render(trip)

    def test_html_safety_and_links(self):
        trip = demo_trip()
        attack = '</script><script>alert(1)</script>@@REPORT@@'
        trip['title'] = attack
        trip['alternatives'][0]['places'][0]['name'] = attack
        output = render(trip)
        self.assertNotIn('</script><script>alert(1)', output)
        self.assertIn('\\u003c/script\\u003e', output)
        ids, targets = [], []

        class Parser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if 'id' in attrs:
                    ids.append(attrs['id'])
                if attrs.get('href', '').startswith('#'):
                    targets.append(attrs['href'][1:])
        Parser().feed(output)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(set(targets).issubset(ids))
        trip['alternatives'][0]['places'][0]['url'] = 'javascript:alert(1)'
        with self.assertRaisesRegex(ValueError, 'HTTP'):
            render(trip)

    def test_cli_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as folder:
            src, dst = Path(folder) / 'trip.json', Path(folder) / 'report.html'
            src.write_text(json.dumps(demo_trip()), encoding='utf-8')
            cmd = [sys.executable, str(Path(__file__).with_name('render_report.py')), str(src), str(dst)]
            first = run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            original = dst.read_bytes()
            second = run(cmd, capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual(dst.read_bytes(), original)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReportTests))
    if not result.wasSuccessful():
        sys.exit(1)
    if args.demo:
        with args.demo.open('x', encoding='utf-8') as file:
            file.write(render(demo_trip(4, 4, 2)))
        print(f'Demo sintetica: {args.demo.resolve()}')
