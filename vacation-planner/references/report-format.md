# Contratto del report

Input JSON UTF-8. Output: un HTML con dati e testi incorporati. Python usa solo libreria standard; Leaflet 1.9.4 viene caricato online solo nell'anteprima HTTP(S). Non occorrono chiavi API. La mappa usa tile OpenStreetMap con attribuzione e referer browser; da `file://` non carica tile. Fonti tecniche: https://leafletjs.com/examples/quick-start/ e https://operations.osmfoundation.org/policies/tiles/.

## Campi

- `title`, `region`, `origin`, `period`, `travelers` (intero positivo), `days` (intero positivo), `currency` (default EUR), `transport`, `party`, `interests`, `room_setup`: riepilogo del viaggio.
- `dates_confirmed`: booleano; indica solo date precise fornite, non prenotazioni confermate. `researched_on`: data ISO della ricerca.
- `budget`: null oppure `{ "amount": "800.00", "scope": "group" }`; scope `group` o `person`. `reserve_percent`: stringa numerica, default `10`.
- `assumptions`, `warnings`: liste di stringhe con ipotesi e incertezze comuni.
- `alternatives`: normalmente 2–4 elementi; 0 o 1 richiedono `fewer_options_reason`, spiegando impossibilità o dati mancanti. Non inserire proposte fuori tetto: renderer le rifiuta. Zero proposte produce comunque un report esplicativo.
- `recommended`: ID della proposta consigliata, obbligatorio quando ci sono alternative.

Ogni alternativa contiene `id` (unico), `name`, `base`, `reason`, `tradeoffs`, `warnings` (lista), `places`, `schedule`, `costs`.

Ogni luogo contiene `id` (unico nella proposta), `kind` (`hotel`, `restaurant`, `attraction`, `transport`), `name`, `address`, `description`, `why`, `url`, `sources` (lista), `coordinates` ([lat, lon] o null), `coordinate_source` (URL se coordinate presenti), `coordinate_note` (motivo se assenti). Per hotel includere tipologia camera, servizi utili e disponibilità non verificata nella descrizione; per attrazioni, storia verificata; per ristoranti, cucina.

Ogni fonte: `{ "url": "https://...", "label": "Menu ufficiale", "checked_on": "2026-09-05" }`. Solo link HTTP(S); prezzi con data, occupazione o periodo diversi devono essere stime per il viaggio corrente, dichiarando la differenza in `note`.

Ogni giorno di `schedule` contiene `day` (1..days, ciascuno una volta), `title`, `overnight` (ID hotel o null), `notes` (meteo/ritorno/altre indicazioni), `events` (lista ordinata). Ogni evento contiene `time` (es. `09:00–10:30`), `title`, `details` (durata e logistica), `place_id` (ID o null). `overnight: null` consente rientro o trasferimento notturno, da spiegare nelle note. Il renderer non deduce giorni e notti: controllarli nel ragionamento.

Ogni voce di `costs` contiene `day`, `category` (`viaggio`, `trasporti`, `alloggi`, `pasti`, `visite`, `tasse`, `extra`), `label`, `place_id` (ID o null), `unit`, `quantity`, `unit_min`, `unit_max`, `basis` (`published_for_dates`, `published_generic`, `estimate`, `included`), `note`, `sources` (lista). Importi e quantità sono stringhe decimali non negative; quantità > 0. `unit_min <= unit_max`. Tariffe pubblicate richiedono almeno una fonte; stime richiedono motivazione. `included` ha prezzo zero e nota su cosa lo include.

Esempio di costo condiviso: 2 camere × 1 notte × 100–120 euro = 200–240 euro, non moltiplicare ancora per persone. Per 3 notti creare una voce per notte/giorno, così i totali giornalieri restano corretti. Esempio pasti: quantità `4`, unità `persona / cena`, prezzo `25`–`35`. Non replicare una spesa sia in un pacchetto sia nelle sue componenti.

Il renderer arrotonda ogni subtotale al centesimo, somma minimi e massimi, calcola riserva sul massimo e verifica `massimo + riserva <= tetto gruppo`. Totali per categoria e giorno escludono la riserva, mostrata a parte. Il dettaglio per luogo si ottiene collegando ogni costo pertinente al suo `place_id`.

## Generazione e verifica

```sh
python3 scripts/render_report.py /percorso/viaggio.json /percorso/itinerario.html
python3 scripts/test_render_report.py
```

Il generatore rifiuta output già esistenti; usare un nome di revisione diverso. Per una dimostrazione esclusivamente sintetica:

```sh
python3 scripts/test_render_report.py --demo /percorso/nuovo-demo.html
```

Il demo prova il prodotto, non è un viaggio ricercato né un preventivo. Per prove comportamentali della skill usare: coppia 2 giorni senza auto; amici 4 giorni con auto e camere condivise; periodo senza date; budget impossibile; fonte prezzi non accessibile. Verificare che chieda dati mancanti, mantenga tempi realistici, dichiari stime e non inventi disponibilità.
