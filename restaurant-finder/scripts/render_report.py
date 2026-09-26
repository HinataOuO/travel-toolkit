#!/usr/bin/env python3
"""Validate restaurant research JSON and render a ranked standalone HTML report."""

from __future__ import annotations

import argparse
import html
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlparse


CRITERIA = ("price", "aesthetic", "style", "booking", "gastronomy", "preferences")
LABELS = {
    "price": "Prezzo",
    "aesthetic": "Estetica",
    "style": "Stile",
    "booking": "Prenotazione",
    "gastronomy": "Gastronomia",
    "preferences": "Preferenze",
}


class ReportError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReportError(message)


def number(value, path: str, *, minimum: float = 0) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{path}: numero richiesto")
    value = float(value)
    require(math.isfinite(value) and value >= minimum, f"{path}: numero non valido")
    return value


def valid_url(value: str) -> bool:
    return isinstance(value, str) and urlparse(value).scheme in {"http", "https"} and bool(urlparse(value).netloc)


def validate_source(source: dict, path: str) -> None:
    require(isinstance(source, dict), f"{path}: oggetto richiesto")
    require(bool(source.get("label")), f"{path}.label: richiesto")
    require(valid_url(source.get("url", "")), f"{path}.url: URL HTTP(S) richiesto")
    try:
        date.fromisoformat(source.get("checked_on", ""))
    except (TypeError, ValueError):
        raise ReportError(f"{path}.checked_on: data ISO richiesta") from None


def price_score(price: dict, budget: dict) -> float | None:
    if not isinstance(price, dict) or "min" not in price or "max" not in price:
        return None
    low = number(price["min"], "price.min")
    high = number(price["max"], "price.max")
    require(low <= high, "price: min deve essere <= max")
    midpoint = (low + high) / 2
    floor = number(budget["min"], "budget.min")
    ceiling = number(budget["max"], "budget.max")
    require(floor <= ceiling and ceiling > 0, "budget: intervallo non valido")
    if floor <= midpoint <= ceiling:
        return 10.0
    distance = floor - midpoint if midpoint < floor else midpoint - ceiling
    ratio = distance / ceiling
    return 8.0 if ratio <= 0.10 else 6.0 if ratio <= 0.25 else 3.0 if ratio <= 0.50 else 0.0


def gastronomy_score(reviews: list) -> float | None:
    if not reviews:
        return None
    weighted = total_weight = 0.0
    for index, review in enumerate(reviews):
        path = f"review_sources[{index}]"
        require(isinstance(review, dict), f"{path}: oggetto richiesto")
        rating = number(review.get("rating"), f"{path}.rating")
        scale = number(review.get("scale"), f"{path}.scale", minimum=0.000001)
        count = number(review.get("count", 0), f"{path}.count")
        require(rating <= scale, f"{path}.rating: supera scale")
        require(bool(review.get("label")), f"{path}.label: richiesto")
        require(valid_url(review.get("url", "")), f"{path}.url: URL HTTP(S) richiesto")
        weight = math.log10(1 + count) if count else 1.0
        weighted += rating / scale * 10 * weight
        total_weight += weight
    return weighted / total_weight


def score_entry(candidate: dict, criterion: str) -> tuple[float | None, bool]:
    entry = candidate.get("scores", {}).get(criterion, {})
    require(isinstance(entry, dict), f"{candidate['id']}.scores.{criterion}: oggetto richiesto")
    applicable = entry.get("applicable", True)
    require(isinstance(applicable, bool), f"{candidate['id']}.scores.{criterion}.applicable: booleano richiesto")
    if not applicable:
        return None, False
    value = entry.get("value")
    if value is None:
        return None, True
    value = number(value, f"{candidate['id']}.scores.{criterion}.value")
    require(value <= 10, f"{candidate['id']}.scores.{criterion}.value: massimo 10")
    require(bool(entry.get("reason")), f"{candidate['id']}.scores.{criterion}.reason: richiesto")
    sources = entry.get("sources", [])
    require(isinstance(sources, list) and sources, f"{candidate['id']}.scores.{criterion}.sources: almeno una fonte")
    require(all(valid_url(url) for url in sources), f"{candidate['id']}.scores.{criterion}.sources: URL HTTP(S) richiesti")
    return value, True


def validate_and_rank(data: dict) -> tuple[list[dict], list[dict]]:
    require(isinstance(data, dict), "radice: oggetto richiesto")
    for key in ("title", "area", "researched_on", "currency", "style_target"):
        require(bool(data.get(key)), f"{key}: richiesto")
    try:
        date.fromisoformat(data["researched_on"])
    except ValueError:
        raise ReportError("researched_on: data ISO richiesta") from None
    for key in ("assumptions", "warnings"):
        require(isinstance(data.get(key, []), list), f"{key}: lista richiesta")
    require(isinstance(data.get("request_summary", {}), dict), "request_summary: oggetto richiesto")

    budget = data.get("budget")
    require(isinstance(budget, dict), "budget: oggetto richiesto")
    number(budget.get("min"), "budget.min")
    number(budget.get("max"), "budget.max")
    require(float(budget["min"]) <= float(budget["max"]) and float(budget["max"]) > 0, "budget: intervallo non valido")

    weights = data.get("weights")
    require(isinstance(weights, dict) and set(weights) == set(CRITERIA), "weights: servono esattamente i sei criteri")
    clean_weights = {key: number(weights[key], f"weights.{key}") for key in CRITERIA}
    require(sum(clean_weights.values()) > 0, "weights: almeno un peso positivo")

    candidates = data.get("candidates")
    require(isinstance(candidates, list) and len(candidates) <= 15, "candidates: lista con massimo 15 elementi")
    ids: set[str] = set()
    ranked, unranked = [], []

    for index, raw in enumerate(candidates):
        require(isinstance(raw, dict), f"candidates[{index}]: oggetto richiesto")
        candidate = dict(raw)
        candidate_id = candidate.get("id")
        require(isinstance(candidate_id, str) and candidate_id and candidate_id not in ids, f"candidates[{index}].id: richiesto e unico")
        ids.add(candidate_id)
        for key in ("name", "kind", "address", "description", "why"):
            require(bool(candidate.get(key)), f"{candidate_id}.{key}: richiesto")
        require(isinstance(candidate.get("scores"), dict), f"{candidate_id}.scores: oggetto richiesto")

        for source_index, source in enumerate(candidate.get("sources", [])):
            validate_source(source, f"{candidate_id}.sources[{source_index}]")
        price_sources = candidate.get("price", {}).get("sources", [])
        require(isinstance(price_sources, list) and price_sources, f"{candidate_id}.price.sources: almeno una fonte")
        for source_index, source in enumerate(price_sources):
            validate_source(source, f"{candidate_id}.price.sources[{source_index}]")
        review_sources = candidate.get("review_sources", [])
        require(isinstance(review_sources, list), f"{candidate_id}.review_sources: lista richiesta")
        for source_index, source in enumerate(review_sources):
            validate_source(source, f"{candidate_id}.review_sources[{source_index}]")
        for link_name, url in candidate.get("links", {}).items():
            require(not url or valid_url(url), f"{candidate_id}.links.{link_name}: URL HTTP(S) richiesto")

        coords = candidate.get("coordinates")
        require(coords is None or (isinstance(coords, list) and len(coords) == 2), f"{candidate_id}.coordinates: coppia [lat, lon] o null richiesta")
        coords_ok = isinstance(coords, list) and len(coords) == 2
        if coords_ok:
            lat = number(coords[0], f"{candidate_id}.coordinates[0]", minimum=-90)
            lon = number(coords[1], f"{candidate_id}.coordinates[1]", minimum=-180)
            coords_ok = lat <= 90 and lon <= 180
            require(coords_ok, f"{candidate_id}.coordinates: fuori intervallo")

        requirements = candidate.get("hard_requirements", [])
        require(isinstance(requirements, list), f"{candidate_id}.hard_requirements: lista richiesta")
        statuses = []
        for req_index, requirement in enumerate(requirements):
            require(isinstance(requirement, dict), f"{candidate_id}.hard_requirements[{req_index}]: oggetto richiesto")
            status = requirement.get("status")
            require(status in {"met", "unverified", "failed"}, f"{candidate_id}.hard_requirements[{req_index}].status: non valido")
            require(bool(requirement.get("label")), f"{candidate_id}.hard_requirements[{req_index}].label: richiesto")
            if requirement.get("source"):
                require(valid_url(requirement["source"]), f"{candidate_id}.hard_requirements[{req_index}].source: URL non valido")
            statuses.append(status)

        computed = {
            "price": price_score(candidate.get("price"), budget),
            "gastronomy": gastronomy_score(review_sources),
        }
        applicable = {criterion: True for criterion in CRITERIA}
        for criterion in ("aesthetic", "style", "booking", "preferences"):
            computed[criterion], applicable[criterion] = score_entry(candidate, criterion)
        candidate["computed_scores"] = computed

        reasons = []
        if not coords_ok:
            reasons.append("coordinate mancanti")
        if any(status != "met" for status in statuses):
            reasons.append("requisiti obbligatori non verificati")
        missing = [LABELS[key] for key in CRITERIA if applicable[key] and computed.get(key) is None and clean_weights[key] > 0]
        if missing:
            reasons.append("punteggi mancanti: " + ", ".join(missing))

        active = [key for key in CRITERIA if applicable[key] and clean_weights[key] > 0]
        total_weight = sum(clean_weights[key] for key in active)
        if total_weight and not reasons:
            candidate["total_score"] = sum(computed[key] * clean_weights[key] for key in active) / total_weight
            ranked.append(candidate)
        else:
            candidate["unranked_reason"] = "; ".join(reasons) or "nessun criterio applicabile"
            unranked.append(candidate)

    ranked.sort(key=lambda item: (
        -item["total_score"],
        -item["computed_scores"]["gastronomy"],
        -item["computed_scores"]["price"],
        -item["computed_scores"]["booking"],
        item["name"].casefold(),
    ))
    for rank, candidate in enumerate(ranked, 1):
        candidate["rank"] = rank
    return ranked, unranked


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def link(url: str, label: str) -> str:
    return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>' if valid_url(url) else ""


def score_bars(candidate: dict) -> str:
    rows = []
    for criterion in CRITERIA:
        value = candidate["computed_scores"].get(criterion)
        if value is None:
            continue
        reason = candidate.get("scores", {}).get(criterion, {}).get("reason", "Calcolato dai dati pubblicati")
        rows.append(
            f'<div class="score"><span>{LABELS[criterion]}</span><meter min="0" max="10" value="{value:.3f}"></meter>'
            f'<strong>{value:.1f}</strong><small>{esc(reason)}</small></div>'
        )
    return "".join(rows)


def source_links(candidate: dict) -> str:
    seen, items = set(), []
    sources = list(candidate.get("sources", [])) + list(candidate.get("price", {}).get("sources", []))
    sources += candidate.get("review_sources", [])
    for source in sources:
        url = source.get("url", "")
        if valid_url(url) and url not in seen:
            seen.add(url)
            stamp = f' · {esc(source.get("checked_on"))}' if source.get("checked_on") else ""
            items.append(f'<li>{link(url, source.get("label", "Fonte"))}{stamp}</li>')
    return f'<ul class="sources">{"".join(items)}</ul>' if items else '<p class="muted">Fonti non elencate.</p>'


def action_links(candidate: dict) -> str:
    labels = {"maps": "Maps", "website": "Sito", "menu": "Menu", "booking": "Prenota"}
    items = [link(url, labels.get(key, key.title())) for key, url in candidate.get("links", {}).items() if url]
    return '<div class="actions">' + "".join(item for item in items if item) + "</div>"


def tags(items: list, css: str) -> str:
    return "".join(f'<span class="tag {css}">{esc(item)}</span>' for item in items)


def render_html(data: dict, ranked: list[dict], unranked: list[dict]) -> str:
    top = ranked[:5]
    summary = data.get("request_summary", {})
    summary_items = "".join(f'<dt>{esc(key.replace("_", " ").title())}</dt><dd>{esc(", ".join(value) if isinstance(value, list) else value)}</dd>' for key, value in summary.items() if value not in (None, "", []))
    ranking_rows = "".join(
        f'<tr data-kind="{esc(c["kind"].casefold())}"><td><button class="focus" data-id="{esc(c["id"])}">{c["rank"]}</button></td>'
        f'<td><strong>{esc(c["name"])}</strong><small>{esc(c["kind"])} · {esc(c["address"])}</small></td>'
        f'<td>{c["total_score"]:.1f}</td><td>{c["computed_scores"]["price"]:.1f}</td>'
        f'<td>{c["computed_scores"]["gastronomy"]:.1f}</td><td>{action_links(c)}</td></tr>' for c in ranked
    )
    top_cards = "".join(
        f'<article class="place" id="place-{esc(c["id"])}" data-kind="{esc(c["kind"].casefold())}">'
        f'<div class="place-head"><span class="rank">#{c["rank"]}</span><div><p class="eyebrow">{esc(c["kind"])} · {esc(c["address"])}</p>'
        f'<h3>{esc(c["name"])}</h3></div><strong class="total">{c["total_score"]:.1f}<small>/10</small></strong></div>'
        f'<p>{esc(c["description"])}</p><p class="why">{esc(c["why"])}</p>'
        f'<p><strong>Prezzo:</strong> {esc(data["currency"])} {float(c["price"]["min"]):.0f}–{float(c["price"]["max"]):.0f} · {esc(c["price"].get("note", ""))}</p>'
        f'{action_links(c)}<div class="scores">{score_bars(c)}</div>'
        f'<div class="proscons"><div><h4>Pro</h4>{tags(c.get("pros", []), "good")}</div><div><h4>Contro</h4>{tags(c.get("cons", []), "bad")}</div></div>'
        f'<details><summary>Fonti</summary>{source_links(c)}</details></article>' for c in top
    )
    unranked_cards = "".join(
        f'<li><strong>{esc(c["name"])}</strong> — {esc(c["unranked_reason"])} {action_links(c)}</li>' for c in unranked
    ) or '<li>Nessun locale escluso o incompleto.</li>'
    weights = ", ".join(f'{LABELS[k]} {float(v):g}%' for k, v in data["weights"].items())
    notices = tags(data.get("warnings", []), "warn") + tags(data.get("assumptions", []), "info")
    map_data = [{"id": c["id"], "name": c["name"], "rank": c.get("rank"), "kind": c["kind"], "coordinates": c.get("coordinates"), "score": c.get("total_score")} for c in ranked + unranked if c.get("coordinates")]
    safe_json = json.dumps(map_data, ensure_ascii=False).replace("</", "<\\/")
    fewer = f'<p class="notice">Solo {len(top)} candidati completi disponibili; report non forza cinque scelte.</p>' if len(top) < 5 else ""

    return f'''<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(data["title"])}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<style>
:root{{--ink:#22211d;--muted:#6d695f;--paper:#f4f0e7;--card:#fffdf8;--accent:#b34e32;--green:#466b52;--line:#d9d1c2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 system-ui,sans-serif}}a{{color:#8e3825}}header,main,footer{{max-width:1180px;margin:auto;padding:28px}}header{{padding-top:64px}}h1{{font:clamp(2.5rem,7vw,5.5rem)/.95 Georgia,serif;max-width:900px;margin:.2em 0}}h2,h3{{font-family:Georgia,serif}}.eyebrow{{text-transform:uppercase;letter-spacing:.12em;font-size:.76rem;color:var(--muted)}}.lede{{max-width:760px;font-size:1.15rem}}.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:28px 0}}.meta div,.panel,.place{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:20px;box-shadow:0 10px 30px #5538200b}}dt{{font-size:.75rem;text-transform:uppercase;color:var(--muted)}}dd{{margin:4px 0 0;font-weight:700}}#map{{height:470px;border-radius:18px;border:1px solid var(--line);background:#ddd5c7}}section{{margin:48px 0}}.filters{{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}}button,.actions a{{border:1px solid var(--line);border-radius:999px;padding:8px 13px;background:var(--card);color:var(--ink);cursor:pointer;text-decoration:none}}button.active,.focus,.actions a:hover{{background:var(--ink);color:white}}table{{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}}th,td{{padding:12px;text-align:left;border-bottom:1px solid var(--line)}}td small{{display:block;color:var(--muted)}}.places{{display:grid;gap:18px}}.place-head{{display:flex;align-items:center;gap:14px}}.place-head h3{{margin:0;font-size:1.7rem}}.rank{{display:grid;place-items:center;background:var(--accent);color:white;border-radius:50%;min-width:48px;height:48px;font-weight:800}}.total{{margin-left:auto;font-size:2rem;color:var(--green)}}.total small{{font-size:.8rem}}.why{{font-weight:650}}.actions{{display:flex;gap:7px;flex-wrap:wrap;margin:12px 0}}.scores{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:20px 0}}.score{{display:grid;grid-template-columns:110px 1fr 32px;gap:8px;align-items:center}}.score small{{grid-column:1/-1;color:var(--muted)}}meter{{width:100%}}.proscons{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.tag{{display:inline-block;padding:5px 9px;margin:3px;border-radius:7px;background:#eee}}.good{{background:#e2eee5;color:#284b33}}.bad,.warn{{background:#f8e3db;color:#74321f}}.info{{background:#e4e8ef;color:#33445e}}.sources{{columns:2}}.notice{{border-left:4px solid var(--accent);padding:12px 16px;background:#f8e3db}}.muted,footer{{color:var(--muted)}}details{{margin-top:16px}}[hidden]{{display:none!important}}
@media(max-width:700px){{header,main,footer{{padding:20px}}header{{padding-top:40px}}#map{{height:360px}}.scores,.proscons{{grid-template-columns:1fr}}.table-wrap{{overflow:auto}}th,td{{white-space:nowrap}}.sources{{columns:1}}}}
</style></head><body>
<header><p class="eyebrow">Restaurant Finder · ricerca del {esc(data["researched_on"])}</p><h1>{esc(data["title"])}</h1><p class="lede">{esc(data["area"])} · budget {esc(data["currency"])} {float(data["budget"]["min"]):.0f}–{float(data["budget"]["max"]):.0f} per persona · stile {esc(data["style_target"])}</p><div>{notices}</div></header>
<main><section class="meta"><div><dt>Area</dt><dd>{esc(data["area"])}</dd></div><div><dt>Candidati classificati</dt><dd>{len(ranked)}</dd></div><div><dt>Top</dt><dd>{len(top)}</dd></div><div><dt>Valuta</dt><dd>{esc(data["currency"])}</dd></div>{summary_items}</section>
<section><p class="eyebrow">Geografia</p><h2>Mappa dei locali</h2><div id="map" role="region" aria-label="Mappa interattiva dei locali"></div><p class="muted">Mappa richiede rete e apertura via server HTTP locale. Dati © OpenStreetMap contributors.</p></section>
<section><p class="eyebrow">Confronto</p><h2>Classifica completa</h2><div class="filters"><button class="active" data-filter="all">Tutti</button>{''.join(f'<button data-filter="{esc(kind.casefold())}">{esc(kind.title())}</button>' for kind in sorted({c["kind"] for c in ranked}))}</div><div class="table-wrap"><table><thead><tr><th>#</th><th>Locale</th><th>Totale</th><th>Prezzo</th><th>Gastronomia</th><th>Link</th></tr></thead><tbody>{ranking_rows}</tbody></table></div>{fewer}</section>
<section><p class="eyebrow">Scelte consigliate</p><h2>Le migliori {len(top)}</h2><div class="places">{top_cards}</div></section>
<section class="panel"><h2>Esclusi o incompleti</h2><ul>{unranked_cards}</ul></section>
<section class="panel"><h2>Metodo</h2><p>Pesi richiesti: {esc(weights)}. Prezzo e gastronomia calcolati dai dati; altri punteggi sono valutazioni editoriali motivate. Criteri non applicabili vengono rinormalizzati. Nessuna disponibilita o prenotazione e garantita.</p></section></main>
<footer>Report generato da Restaurant Finder · contenuti verificati alla data indicata.</footer>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><script>
const places={safe_json};
if(window.L&&places.length){{const clean=s=>String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));const map=L.map('map');L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}}).addTo(map);const markers={{}};const bounds=[];for(const p of places){{const marker=L.marker(p.coordinates).addTo(map).bindPopup(`<strong>${{p.rank?'#'+p.rank+' ':''}}${{clean(p.name)}}</strong><br>${{clean(p.kind)}}${{p.score!=null?'<br>'+p.score.toFixed(1)+'/10':''}}`);markers[p.id]=marker;bounds.push(p.coordinates)}}map.fitBounds(bounds,{{padding:[28,28],maxZoom:15}});document.querySelectorAll('.focus').forEach(b=>b.addEventListener('click',()=>{{const m=markers[b.dataset.id];if(m){{map.setView(m.getLatLng(),16);m.openPopup();document.getElementById('map').scrollIntoView({{behavior:'smooth'}})}}}}))}}else{{document.getElementById('map').innerHTML='<p style="padding:2rem">Mappa non disponibile. Usa link Maps nelle schede.</p>'}}
document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{{document.querySelectorAll('[data-filter]').forEach(b=>b.classList.remove('active'));button.classList.add('active');const wanted=button.dataset.filter;document.querySelectorAll('[data-kind]').forEach(row=>row.hidden=wanted!=='all'&&row.dataset.kind!==wanted)}}));
</script></body></html>'''


def render(input_path: Path, output_path: Path) -> None:
    require(input_path.is_file(), f"input non trovato: {input_path}")
    require(not output_path.exists(), f"output esiste gia: {output_path}")
    with input_path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    ranked, unranked = validate_and_rank(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(data, ranked, unranked), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        render(args.input.resolve(), args.output.resolve())
    except (OSError, json.JSONDecodeError, ReportError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
