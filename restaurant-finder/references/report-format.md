# Contratto dati e punteggi

Input JSON UTF-8; output HTML autosufficiente per contenuti. Leaflet 1.9.4 e tile OpenStreetMap vengono caricati solo per mappa online. Nessuna chiave API.

## Richiesta

Campi radice obbligatori:

- `title`, `area`, `researched_on` (data ISO), `currency`;
- `budget`: `{ "min": 25, "max": 40, "basis": "persona / pasto tipico" }`, con numeri non negativi e `min <= max`;
- `style_target`, `request_summary`;
- `weights`: oggetto con tutti i criteri `price`, `aesthetic`, `style`, `booking`, `gastronomy`, `preferences`;
- `candidates`: massimo 15 elementi;
- `assumptions` e `warnings`: liste di stringhe.

`request_summary` puo contenere `party_size`, `date_time`, `cuisines`, `soft_preferences` e altre informazioni utili. Il renderer lo presenta senza interpretarlo.

## Candidato

Ogni candidato contiene:

```json
{
  "id": "osteria-esempio",
  "name": "Osteria Esempio",
  "kind": "ristorante",
  "address": "Via Esempio 1, Roma",
  "coordinates": [41.9, 12.5],
  "description": "Cucina regionale in sale raccolte.",
  "why": "Buon equilibrio tra atmosfera e budget.",
  "price": {
    "min": 28,
    "max": 38,
    "note": "Stima da menu corrente.",
    "sources": [{"label": "Menu ufficiale", "url": "https://example.com/menu", "checked_on": "2026-09-09"}]
  },
  "review_sources": [
    {"label": "Google Maps", "rating": 4.5, "scale": 5, "count": 420, "url": "https://example.com/reviews", "checked_on": "2026-09-09"}
  ],
  "booking": {"method": "direct_instant", "note": "Conferma immediata", "url": "https://example.com/book"},
  "links": {"maps": "https://www.google.com/maps/search/?api=1&query=...", "website": "https://example.com", "menu": "https://example.com/menu", "booking": "https://example.com/book"},
  "hard_requirements": [{"label": "senza glutine", "status": "met", "note": "Menu dedicato", "source": "https://example.com/menu"}],
  "scores": {
    "aesthetic": {"value": 8, "reason": "Sale curate e coerenti", "sources": ["https://example.com/gallery"]},
    "style": {"value": 9, "reason": "Forte corrispondenza rustica", "sources": ["https://example.com/gallery"]},
    "booking": {"value": 10, "reason": "Motore diretto con conferma", "sources": ["https://example.com/book"]},
    "preferences": {"value": 7, "reason": "Dehors disponibile", "sources": ["https://example.com"], "applicable": true}
  },
  "pros": ["Menu nel budget"],
  "cons": ["Pochi tavoli esterni"],
  "sources": [{"label": "Sito ufficiale", "url": "https://example.com", "checked_on": "2026-09-09"}]
}
```

`coordinates` puo essere `null`; candidato resta senza marker e non entra in classifica. `kind` e testo libero breve (`ristorante`, `pizzeria`, `trattoria`, ecc.). ID unici.

Fonti usano solo URL HTTP(S). Link mancanti possono essere omessi o stringa vuota. Stato hard requirement: `met`, `unverified`, `failed`. Solo candidati con tutti hard requirement `met`, coordinate valide, prezzo, recensioni e punteggi applicabili completi entrano in classifica.

## Calcoli

- Prezzo: usa punto medio di `price.min`/`price.max`. 10 se entro budget; fuori range assegna 8 entro 10% del massimo budget, 6 entro 25%, 3 entro 50%, 0 oltre.
- Gastronomia: normalizza ogni rating con `rating / scale * 10`; media usando peso `log10(1 + count)`, o peso 1 quando count e zero. Mostra rating e volume originali.
- Totale: media pesata dei sei criteri. Criteri con `applicable: false` vengono esclusi e pesi restanti rinormalizzati. Valore mancante non viene rinormalizzato: candidato diventa incompleto.
- Ordine: totale decrescente; poi gastronomia, prezzo, prenotazione; infine nome alfabetico. Arrotondamento visivo a un decimale.
- Prime cinque posizioni diventano raccomandazioni approfondite. Se classifica completa contiene meno di cinque locali, report spiega motivo.

## Evidenza e limiti

Ogni punteggio editoriale richiede motivo e almeno una fonte. Non usare recensioni singole come fatto generale; riassumi temi ricorrenti solo quando verificabili. Dati discordanti restano visibili in `warnings` o note. Locali incompleti e quelli esclusi da hard filter compaiono separatamente, senza rango.

Mappa usa `https://tile.openstreetmap.org/{z}/{x}/{y}.png`, attribuzione visibile, cache browser normale e niente prefetch. Link Maps usa `https://www.google.com/maps/search/?api=1&query=...`; preferire nome e indirizzo, oppure Place ID quando disponibile.
