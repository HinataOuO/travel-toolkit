#!/usr/bin/env python3
"""Render a researched trip JSON as a standalone, offline-readable HTML report."""

import argparse
import html
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import quote, urlsplit

CENT = Decimal('0.01')
CATEGORIES = ('viaggio', 'trasporti', 'alloggi', 'pasti', 'visite', 'tasse', 'extra')
KINDS = {'hotel': 'Alloggio', 'restaurant': 'Ristorante', 'attraction': 'Visita', 'transport': 'Trasporto'}
BASES = {'published_for_dates': 'Prezzo pubblicato per le date', 'published_generic': 'Tariffa generica', 'estimate': 'Stima', 'included': 'Incluso'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f'Numero non valido: {value!r}') from None
    require(n.is_finite() and n >= 0, f'Importo o quantità non valido: {value!r}')
    return n


def rounded(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def esc(value):
    return html.escape(str(value), quote=True)


def url(value):
    parsed = urlsplit(str(value))
    require(parsed.scheme in ('https', 'http') and parsed.hostname, f'URL HTTP(S) richiesto: {value!r}')
    return esc(value)


def link(value, label):
    return f'<a href="{url(value)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'


def source_list(sources):
    parts = []
    for s in sources:
        date.fromisoformat(s['checked_on'])
        parts.append(link(s['url'], s['label']) + ' · ' + esc(s['checked_on']))
    return '<br>'.join(parts)


def money(value, currency):
    formatted = f'{rounded(value):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    return f'{formatted} {esc(currency)}'


def interval(low, high, currency):
    return money(low, currency) if low == high else f'{money(low, currency)} – {money(high, currency)}'


def bullets(items):
    return '<ul>' + ''.join(f'<li>{esc(item)}</li>' for item in items) + '</ul>' if items else ''


def prepare(data):
    people, days = data['travelers'], data['days']
    require(type(people) is int and people > 0, 'travelers deve essere un intero positivo')
    require(type(days) is int and days > 0, 'days deve essere un intero positivo')
    require(type(data['dates_confirmed']) is bool, 'dates_confirmed deve essere booleano')
    date.fromisoformat(data['researched_on'])
    currency = data.get('currency', 'EUR')
    require(re.fullmatch('[A-Z]{3}', currency), 'currency deve essere un codice di tre lettere')
    reserve = number(data.get('reserve_percent', '10'))
    budget = data.get('budget')
    cap = None
    if budget is not None:
        require(budget['scope'] in ('person', 'group'), 'budget.scope deve essere person o group')
        cap = number(budget['amount']) * (people if budget['scope'] == 'person' else 1)
    alternatives = data['alternatives']
    require(len(alternatives) <= 4, 'Massimo quattro alternative')
    if len(alternatives) < 2:
        require(data.get('fewer_options_reason', '').strip(), 'Spiegare perché ci sono meno di due alternative')
    ids = [a['id'] for a in alternatives]
    require(len(ids) == len(set(ids)), 'ID alternativa duplicato')
    if alternatives:
        require(data.get('recommended') in ids, 'Proposta consigliata non trovata')
    prepared = []
    for a in alternatives:
        places = {p['id']: p for p in a['places']}
        require(len(places) == len(a['places']), 'ID luogo duplicato')
        for p in places.values():
            require(p['kind'] in KINDS, 'Tipo luogo sconosciuto')
            url(p['url'])
            source_list(p['sources'])
            require(p['sources'], f"Fonti mancanti per {p['name']}")
            coords = p['coordinates']
            if coords is not None:
                require(isinstance(coords, list) and len(coords) == 2 and all(type(v) in (int, float) for v in coords), 'Coordinate numeriche [lat, lon] richieste')
                require(-90 <= coords[0] <= 90 and -180 <= coords[1] <= 180, 'Coordinate fuori intervallo')
                url(p['coordinate_source'])
            else:
                require(p.get('coordinate_note', '').strip(), 'Spiegare coordinate mancanti')
        schedule = a['schedule']
        require(all(type(d['day']) is int for d in schedule), 'Giorni interi richiesti')
        require(sorted(d['day'] for d in schedule) == list(range(1, days + 1)), 'Programma deve coprire ogni giorno esattamente una volta')
        for day in schedule:
            overnight = day['overnight']
            require(overnight is None or overnight in places and places[overnight]['kind'] == 'hotel', 'Pernottamento deve riferirsi a un hotel')
            for event in day['events']:
                require(event['place_id'] is None or event['place_id'] in places, 'Luogo evento non trovato')
        costs, categories, daily = [], {}, {}
        for c in a['costs']:
            require(type(c['day']) is int and 1 <= c['day'] <= days, 'Giorno costo fuori intervallo')
            require(c['category'] in CATEGORIES, 'Categoria costo sconosciuta')
            require(c['place_id'] is None or c['place_id'] in places, 'Luogo costo non trovato')
            require(c['basis'] in BASES, 'Base prezzo sconosciuta')
            quantity, low, high = (number(c[k]) for k in ('quantity', 'unit_min', 'unit_max'))
            require(quantity > 0 and low <= high, 'Quantità deve essere positiva e minimo <= massimo')
            require(c['note'].strip(), 'Nota del prezzo obbligatoria')
            if c['basis'].startswith('published'):
                require(c['sources'], 'Tariffa pubblicata richiede una fonte')
            if c['basis'] == 'included':
                require(high == 0, 'Una voce inclusa deve costare zero')
            source_list(c['sources'])
            row = dict(c, low=rounded(low * quantity), high=rounded(high * quantity))
            costs.append(row)
            for group, key in ((categories, c['category']), (daily, c['day'])):
                totals = group.setdefault(key, [Decimal(0), Decimal(0)])
                totals[0] += row['low']
                totals[1] += row['high']
        require(costs, 'Una proposta completa deve contenere costi')
        low = sum((c['low'] for c in costs), Decimal(0))
        high = sum((c['high'] for c in costs), Decimal(0))
        contingency = rounded(high * reserve / 100)
        require(cap is None or high + contingency <= cap, f"{a['name']}: massimo con riserva {high + contingency} oltre tetto {cap}")
        prepared.append(dict(a, costs=costs, categories=categories, daily=daily, low=low, high=high, contingency=contingency, total=high + contingency))
    return sorted(prepared, key=lambda a: a['total']), cap, reserve, currency


def render(data):
    alternatives, cap, reserve, currency = prepare(data)
    people = data['travelers']
    out = [f'<header><p class="eyebrow">IL TUO VIAGGIO · {esc(data["region"])}</p><h1>{esc(data["title"])}</h1>',
           f'<p class="lead">{esc(data["period"])} · {data["days"]} giorni · {people} persone</p>',
           '<dl class="brief">' + ''.join(f'<div><dt>{label}</dt><dd>{esc(data[key])}</dd></div>' for key, label in [('origin', 'Partenza'), ('transport', 'Trasporti'), ('party', 'Compagnia'), ('interests', 'Interessi'), ('room_setup', 'Camere')]) + '</dl>',
           f'<p>Ricerca: {esc(data["researched_on"])}. Prezzi soggetti a variazioni; nessuna prenotazione o disponibilità garantita.</p></header>']
    if not data['dates_confirmed']:
        out.append('<aside class="notice">Report preliminare: date precise mancanti. Prezzi stagionali indicativi; orari e disponibilità da verificare.</aside>')
    out.append(bullets(data.get('warnings', [])))
    out.append('<details><summary>Ipotesi usate</summary>' + bullets(data.get('assumptions', [])) + '</details>')
    cap_text = money(cap, currency) if cap is not None else 'non indicato'
    out.append(f'<section aria-labelledby="compare"><h2 id="compare">Le alternative</h2><p>Tetto gruppo: {cap_text}. Riserva: {esc(reserve)}% del massimo stimato, inclusa nel confronto.</p>')
    if data.get('fewer_options_reason'):
        out.append(f'<p class="notice">{esc(data["fewer_options_reason"])}</p>')
    out.append('<div class="comparison">')
    for i, a in enumerate(alternatives):
        recommended = a['id'] == data['recommended']
        out.append(f'<article class="choice"><p class="eyebrow">{"CONSIGLIATA" if recommended else "ALTERNATIVA"}</p><h3>{esc(a["name"])}</h3><p>{esc(a["base"])}</p><p class="price">{money(a["total"], currency)}</p><p>Massimo gruppo, riserva inclusa<br>{money(a["total"] / people, currency)} / persona in media</p><p>{esc(a["reason"])}</p><button type="button" data-select="{i}" aria-controls="option-{i}" aria-pressed="true">Esplora {esc(a["name"])}</button></article>')
    out.append('</div></section>')
    map_data = []
    for i, a in enumerate(alternatives):
        anchors = {p['id']: f'place-{i}-{j}' for j, p in enumerate(a['places'])}
        out.append(f'<section class="option" id="option-{i}" data-option="{i}"><h2>{esc(a["name"])} · {esc(a["base"])}</h2><p>{esc(a["reason"])}</p><p><strong>Compromessi:</strong> {esc(a["tradeoffs"])}</p>' + bullets(a.get('warnings', [])))
        out.append(f'<label class="day-filter">Giornata <select data-day-select="{i}"><option value="all">Tutte le giornate</option>' + ''.join(f'<option value="{n}">Giorno {n}</option>' for n in range(1, data['days'] + 1)) + '</select></label>')
        for d in sorted(a['schedule'], key=lambda d: d['day']):
            out.append(f'<article class="day" data-day="{d["day"]}"><h3>Giorno {d["day"]} · {esc(d["title"])}</h3><ol class="timeline">')
            for e in d['events']:
                place_link = f' <a href="#{anchors[e["place_id"]]}" data-focus="{anchors[e["place_id"]]}">Scheda luogo</a>' if e['place_id'] else ''
                out.append(f'<li><span class="time">{esc(e["time"])}</span><div><strong>{esc(e["title"])}</strong><p>{esc(e["details"])}</p>{place_link}</div></li>')
            out.append('</ol>')
            if d['overnight']:
                p = next(p for p in a['places'] if p['id'] == d['overnight'])
                out.append(f'<p><strong>Pernottamento:</strong> <a href="#{anchors[p["id"]]}" data-focus="{anchors[p["id"]]}">{esc(p["name"])}</a></p>')
            else:
                out.append('<p><strong>Pernottamento:</strong> nessun alloggio previsto per questa notte.</p>')
            out.append(f'<p>{esc(d["notes"])}</p></article>')
        out.append('<h3>Luoghi e soggiorni</h3><div class="places">')
        mapped = []
        for p in a['places']:
            anchor = anchors[p['id']]
            used_days = sorted({d['day'] for d in a['schedule'] if d['overnight'] == p['id'] or any(e['place_id'] == p['id'] for e in d['events'])})
            linked_costs = [c for c in a['costs'] if c['place_id'] == p['id']]
            out.append(f'<article class="place" id="{anchor}" tabindex="-1"><p class="eyebrow">{KINDS[p["kind"]]}</p><h4>{esc(p["name"])}</h4><p>{esc(p["address"])}</p><p>{esc(p["description"])}</p><p><strong>Perché qui:</strong> {esc(p["why"])}</p>')
            for c in linked_costs:
                out.append(f'<p class="place-cost">G{c["day"]} · {esc(c["label"])}: {interval(number(c["unit_min"]), number(c["unit_max"]), currency)} / {esc(c["unit"])} · {esc(c["quantity"])} unità · subtotale {interval(c["low"], c["high"], currency)}</p>')
            maps_url = 'https://www.google.com/maps/search/?api=1&query=' + quote(p['name'] + ' ' + p['address'])
            out.append('<p>' + link(p['url'], 'Sito / dettagli') + ' · ' + link(maps_url, 'Apri in Maps') + '</p>')
            if p['coordinates'] is not None:
                out.append(f'<button class="map-action" type="button" data-focus="{anchor}">Mostra sulla mappa</button><p class="sources">Coordinate: {link(p["coordinate_source"], "fonte cartografica")}</p>')
            else:
                out.append(f'<p class="notice">Posizione non verificata: {esc(p["coordinate_note"])}</p>')
            out.append('<details><summary>Fonti</summary><p class="sources">' + source_list(p['sources']) + '</p></details></article>')
            mapped.append({'anchor': anchor, 'name': p['name'], 'kind': p['kind'], 'coordinates': p['coordinates'], 'days': used_days})
        out.append('</div><h3>Budget dettagliato</h3><div class="totals">')
        for label, value in [('Spese previste', interval(a['low'], a['high'], currency)), ('Riserva imprevisti', money(a['contingency'], currency)), ('Massimo con riserva', money(a['total'], currency)), ('Quota media / persona', money(a['total'] / people, currency))]:
            out.append(f'<div><span>{label}</span><strong>{value}</strong></div>')
        if cap is not None:
            out.append(f'<div><span>Margine residuo sul tetto</span><strong>{money(cap - a["total"], currency)}</strong></div>')
        out.append('</div><div class="breakdown"><div><h4>Per categoria</h4>')
        out.append(bullets([f'{k.capitalize()}: {interval(*v, currency)}' for k, v in a['categories'].items()]))
        out.append('</div><div><h4>Per giorno · riserva esclusa</h4>')
        out.append(bullets([f'Giorno {n}: {interval(*a["daily"].get(n, (Decimal(0), Decimal(0))), currency)}' for n in range(1, data['days'] + 1)]))
        out.append('</div></div><div class="table-scroll" role="region" aria-label="Dettaglio costi" tabindex="0"><table><caption>Ogni spesa, con quantità e base del prezzo. Riserva separata.</caption><thead><tr><th scope="col">Giorno / voce</th><th scope="col">Quantità</th><th scope="col">Prezzo unitario</th><th scope="col">Subtotale</th><th scope="col">Attendibilità e fonti</th></tr></thead><tbody>')
        for c in a['costs']:
            out.append(f'<tr><th scope="row">G{c["day"]} · {esc(c["label"])}<br><small>{esc(c["category"])}</small></th><td>{esc(c["quantity"])} × {esc(c["unit"])}</td><td>{interval(number(c["unit_min"]), number(c["unit_max"]), currency)}</td><td>{interval(c["low"], c["high"], currency)}</td><td><strong>{BASES[c["basis"]]}</strong><br>{esc(c["note"])}<br>{source_list(c["sources"])}</td></tr>')
        out.append('</tbody></table></div></section>')
        map_data.append(mapped)
    out.append('<footer>Documento di pianificazione, non preventivo vincolante. Verifica disponibilità, condizioni e prezzi prima di prenotare. Costi individuali esposti come media del gruppo.</footer>')
    payload = {'options': map_data, 'recommended': next((i for i, a in enumerate(alternatives) if a['id'] == data.get('recommended')), 0)}
    safe_json = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    template = (Path(__file__).resolve().parent.parent / 'assets/report.html').read_text(encoding='utf-8')
    # Substitute in one pass so source text cannot become a template directive.
    values = {'TITLE': esc(data['title']), 'REPORT': ''.join(out), 'MAP_DATA': safe_json}
    return re.sub(r'@@(TITLE|REPORT|MAP_DATA)@@', lambda m: values[m[1]], template)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        result = render(json.loads(args.input.read_text(encoding='utf-8')))
        with args.output.open('x', encoding='utf-8') as destination:
            destination.write(result)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(1, f'Errore: {error}\n')
    print(f'Report creato: {args.output.resolve()}')


if __name__ == '__main__':
    main()
