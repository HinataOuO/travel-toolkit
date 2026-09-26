---
name: vacation-planner
description: Organizza vacanze e brevi soggiorni con ricerca web, scelta delle località, 2–4 itinerari per fascia di costo e report HTML con mappa e budget dettagliato. Usa per pianificare o rivedere un viaggio; non per prenotare o pagare.
---

# Vacation planner

Trasforma una richiesta di vacanza in alternative percorribili e un file HTML da portare in viaggio. Lavora in chat, senza API di prenotazione, account aggiuntivi o profilo personale persistente. Il report usa italiano naturale, euro salvo richiesta diversa. Non applicare stile telegrafico alle descrizioni del report.

## Raccogli il necessario

Recupera prima quanto già detto. Chiedi insieme solo dati mancanti che cambiano sostanzialmente il viaggio: regione/destinazione, città di partenza, date o periodo, durata e orari di partenza/rientro, numero di persone e composizione delle camere, mezzo di trasporto, interessi e ritmo, budget e se per persona o gruppo. Chiedi esigenze alimentari/accessibilità quando rilevanti. Non dedurre interessi da stereotipi su coppie o gruppi.

Quattro giorni è un esempio, non una durata fissa. Conta notti e giorni separatamente; andata e ritorno consumano tempo. Con periodo ma senza date precise prepara un preliminare dichiarato, senza sostenere che disponibilità, orari o prezzi siano confermati. Senza partenza, persone, durata o ambito del budget, risolvi le ambiguità prima di calcolare il totale. Se manca un tetto e l'utente vuole esplorare, confronta le fasce senza inventarne uno.

## Ricerca e costruisci le alternative

- Usa ricerca web aggiornata per ogni viaggio reale. Preferisci siti ufficiali di strutture, menu, enti turistici, attrazioni e trasporti. Apri le fonti utili: uno snippet non prova una tariffa. Registra URL, data consultazione e cosa supporta ogni fonte. Non aggirare blocchi: cerca fonti alternative e dichiara le lacune.
- Scegli 2–4 soluzioni, tre di default: economica, equilibrata, comfort. Possono cambiare base e itinerario; tutte devono soddisfare esigenze e tetto. Ordinale per totale massimo con riserva e motiva una raccomandazione. Non moltiplicare opzioni quasi identiche per riempire le fasce.
- Valuta località rispetto a stagione, interessi, compagnia e mezzi. Per soggiorni brevi preferisci una base quando riduce trasferimenti inutili. Verifica tempi porta a porta, parcheggi, coincidenze, giorni di chiusura, check-in e margini. Evita giornate piene senza pause. Se mancano dati, usa intervalli prudenti esplicitamente stimati.
- Per ogni giorno indica sequenza e durata di tappe, trasferimenti, pasti e alloggio della notte; ultimo giorno include rientro. Prevedi un'alternativa al maltempo per attività esposte, senza contarla insieme all'attività sostituita.
- Usa hotel, ristoranti e attrazioni reali con indirizzo, link e fonti. Per visite: breve storia verificata e ragione della scelta. Per hotel: sistemazione proposta, posizione, servizi rilevanti, vantaggi e compromessi. Per pasti: cucina, esigenze compatibili e costo per persona.
- Verifica coordinate con una fonte cartografica o ufficiale. Coordinate ignote restano null, con motivo e link di ricerca; mai usare centro città come posizione precisa dell'hotel. Non presentare segmenti in linea d'aria come percorsi reali.
- Distingui prezzo pubblicato per date/ospiti richiesti, tariffa generica e stima. Disponibilità non verificata resta tale anche quando trovi un prezzo. Non inventare nomi, recensioni, storia, prezzi o fonti.

## Budget completo

Conta viaggio A/R, trasporti locali, camere, pasti, ingressi, tasse ed extra applicabili. Usa costi condivisi per veicolo/camera e individuali per persona; niente moltiplicazione indiscriminata per partecipanti. Colazione inclusa e attività alternative non vanno sommate due volte. Distribuisci una spesa su giorni solo una volta.

Per ogni voce registra giorno, luogo se pertinente, unità, quantità, prezzo unitario minimo/massimo, base del prezzo e fonte o motivazione della stima. Il generatore calcola subtotali e totali con Decimal; non scrivere totali a mano. Riserva separata del 10% del massimo stimato, modificabile. Con tetto per persona, converti in tetto gruppo; quota individuale esposta come media, non promessa di ripartizione equa.

Il massimo stimato più riserva deve stare nel tetto. Se non trovi abbastanza soluzioni, fornisci meno proposte con spiegazione; zero se nessuna è fattibile. Indica deficit stimato e modifiche possibili, senza abbassare silenziosamente requisiti o rimuovere costi. Se una spesa necessaria non ha neppure una stima difendibile, non presentare una proposta come economicamente verificata: spiega cosa manca e prepara il report senza proposte complete.

## Genera e consegna

Leggi [references/report-format.md](references/report-format.md) prima di preparare dati o usare il generatore. Crea JSON del viaggio e HTML in una cartella del workspace scelta per quel viaggio, non dentro la skill. Conserva JSON accanto al report per revisioni; non scrivere profili trasversali ai viaggi. Usa nomi nuovi per revisioni, preservando report precedenti.

Dalla cartella della skill esegui, usando percorsi assoluti per i file del viaggio:

```sh
python3 scripts/render_report.py /percorso/viaggio.json /percorso/itinerario.html
```

Rileggi il report e verifica calcoli, numero notti, tempi, copertura pasti, fonti, selettori e associazione punti/schede. Consegnalo con link cliccabile e una frase sulla proposta consigliata e sull'incertezza principale. Il JSON è supporto alle revisioni, l'HTML è il prodotto per l'utente.

Testi, costi e selettori funzionano offline. La mappa richiede rete; da file locale mostra istruzioni per anteprima HTTP e link esterni. Per attivarla, dalla cartella del report:

```sh
python3 -m http.server 8765 --bind 127.0.0.1
```

Aprire `http://127.0.0.1:8765/itinerario.html`. Servire soltanto la cartella del viaggio. Non pubblicare il report o avviare un server pubblico. Cartografia OpenStreetMap con attribuzione, cache browser normale, niente prefetch. Nessuna prenotazione, pagamento o contatto con strutture.

Per una revisione, riparti dal JSON, aggiorna fonti e dati interessati, ricalcola tutto e genera un nuovo HTML. Non limitarti a cambiare il totale visibile.
