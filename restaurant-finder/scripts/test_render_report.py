#!/usr/bin/env python3
"""Small stdlib test suite and synthetic demo for render_report.py."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from render_report import ReportError, render, validate_and_rank


def candidate(candidate_id: str, name: str, *, aesthetic: float = 8, requirements=None) -> dict:
    checked = "2026-09-09"
    source = {"label": "Sito ufficiale", "url": f"https://example.com/{candidate_id}", "checked_on": checked}
    return {
        "id": candidate_id,
        "name": name,
        "kind": "pizzeria" if candidate_id == "forno" else "ristorante",
        "address": "Via Demo 1, Roma",
        "coordinates": [41.9 + len(candidate_id) / 1000, 12.5],
        "description": "Locale sintetico usato per verificare il renderer.",
        "why": "Esempio con dati completi, non raccomandazione reale.",
        "price": {"min": 25, "max": 35, "note": "Demo", "sources": [source]},
        "review_sources": [{"label": "Recensioni demo", "rating": 4.5, "scale": 5, "count": 200, "url": source["url"], "checked_on": checked}],
        "booking": {"method": "direct_instant", "note": "Demo", "url": source["url"]},
        "links": {"maps": f"https://www.google.com/maps/search/?api=1&query={candidate_id}", "website": source["url"]},
        "hard_requirements": requirements or [],
        "scores": {
            "aesthetic": {"value": aesthetic, "reason": "Rubrica demo", "sources": [source["url"]]},
            "style": {"value": 8, "reason": "Rubrica demo", "sources": [source["url"]]},
            "booking": {"value": 10, "reason": "Conferma immediata demo", "sources": [source["url"]]},
            "preferences": {"applicable": False},
        },
        "pros": ["Dato completo"],
        "cons": ["Solo demo"],
        "sources": [source],
    }


def demo_data() -> dict:
    return {
        "title": "Dove mangiare a Trastevere",
        "area": "Trastevere, entro 2 km",
        "researched_on": "2026-09-09",
        "currency": "EUR",
        "budget": {"min": 25, "max": 40, "basis": "persona / pasto tipico"},
        "style_target": "rustico",
        "request_summary": {"party_size": 2, "cuisines": ["romana", "pizza"]},
        "weights": {"price": 22, "aesthetic": 18, "style": 14, "booking": 18, "gastronomy": 18, "preferences": 10},
        "assumptions": ["Demo sintetica: nessun locale reale"],
        "warnings": ["Prezzi e disponibilita non reali"],
        "candidates": [candidate("osteria", "Osteria Demo", aesthetic=9), candidate("forno", "Forno Demo", aesthetic=7)],
    }


class RendererTests(unittest.TestCase):
    def test_scores_orders_and_renders(self):
        data = demo_data()
        ranked, unranked = validate_and_rank(data)
        self.assertEqual([item["id"] for item in ranked], ["osteria", "forno"])
        self.assertFalse(unranked)
        self.assertEqual(ranked[0]["computed_scores"]["price"], 10)
        self.assertAlmostEqual(ranked[0]["computed_scores"]["gastronomy"], 9)
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "data.json"
            target = Path(temp) / "report.html"
            source.write_text(json.dumps(data), encoding="utf-8")
            render(source, target)
            output = target.read_text(encoding="utf-8")
            self.assertIn("Osteria Demo", output)
            self.assertIn("OpenStreetMap contributors", output)

    def test_hard_filter_and_missing_score_are_unranked(self):
        data = demo_data()
        data["candidates"][0]["hard_requirements"] = [{"label": "accessibile", "status": "unverified"}]
        data["candidates"][1]["scores"]["booking"]["value"] = None
        ranked, unranked = validate_and_rank(data)
        self.assertFalse(ranked)
        self.assertEqual(len(unranked), 2)

    def test_rejects_duplicate_id(self):
        data = demo_data()
        data["candidates"][1]["id"] = data["candidates"][0]["id"]
        with self.assertRaises(ReportError):
            validate_and_rank(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", type=Path)
    args, remaining = parser.parse_known_args()
    if args.demo:
        require_new = not args.demo.exists()
        if not require_new:
            parser.error(f"output esiste gia: {args.demo}")
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "demo.json"
            source.write_text(json.dumps(demo_data(), ensure_ascii=False, indent=2), encoding="utf-8")
            render(source, args.demo.resolve())
        print(args.demo.resolve())
        return
    unittest.main(argv=[__file__, *remaining])


if __name__ == "__main__":
    main()
