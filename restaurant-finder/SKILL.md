---
name: restaurant-finder
description: Trova e classifica ristoranti, pizzerie e altri locali in una zona usando prezzo, atmosfera, stile, prenotazione e recensioni, poi genera un report HTML con mappa. Usa per scegliere dove mangiare; non per prenotare, pagare o contattare locali.
---

# Restaurant finder

Trasforma una richiesta su dove mangiare in una classifica verificabile e in un report HTML italiano. Usa EUR salvo richiesta diversa. Non applicare stile telegrafico ai testi del report.

## Definisci la ricerca

Recupera prima quanto gia detto. Chiedi solo dati mancanti che cambiano davvero il risultato:

- zona come quartiere, centro con raggio, oppure link Maps; se confine resta ambiguo, chiedi centro e raggio;
- range di spesa per persona per un pasto tipico (coperto, una portata e bevanda base, salvo formula diversa dichiarata);
- stile cercato, almeno `rustico`, `elegante` o `indifferente`;
- numero persone, data/ora se rilevanti, cucina, preferenze e requisiti obbligatori;
- pesi solo quando utente vuole modificarli.

Allergie, accessibilita e condizioni definite obbligatorie sono hard filter: includi nelle raccomandazioni solo locali con compatibilita verificata. Cucina, dehors o altre preferenze morbide alimentano invece punteggio `preferences`.

## Ricerca e valuta

Usa ricerca web aggiornata. Cerca fino a 15 candidati reali entro area richiesta; non riempire quota con locali deboli o duplicati. Preferisci sito, menu e prenotazione ufficiali; integra con Maps e piattaforme di recensioni. Apri fonti utili: snippet solo non basta. Registra URL, data consultazione e dato supportato.

Leggi [references/report-format.md](references/report-format.md) prima di preparare JSON. Applica rubriche documentate. Prezzo e gastronomia vengono calcolati dal renderer; per estetica, stile, prenotazione e preferenze assegna valore 0-10 con motivazione concreta e fonti. Estetica e stile sono giudizi editoriali: dichiaralo, cita immagini o descrizioni consultate, non copiare fotografie nel report.

Default pesi: `price` 22, `aesthetic` 18, `style` 14, `booking` 18, `gastronomy` 18, `preferences` 10. Se `preferences` non e applicabile, imposta `applicable: false`; renderer rinormalizza. Con pesi personalizzati accetta numeri non negativi con almeno un criterio positivo.

Prenotazione:

- 10: motore diretto con disponibilita e conferma immediata;
- 8: piattaforma terza con conferma immediata;
- 6: modulo diretto o WhatsApp senza conferma immediata;
- 4: solo telefono o messaggio social;
- 2: contatto incerto;
- 0: canale assente o non verificato.

Non dichiarare disponibilita se data, ora e numero persone non sono verificabili pubblicamente. Non avviare prenotazioni, login, pagamenti o contatti.

## Genera e consegna

Crea una nuova cartella `restaurant-reports/<zona>-<data>/` nel workspace. Salva JSON e HTML insieme; per revisioni usa nuovo nome, senza sovrascrivere. Dalla cartella skill esegui:

```sh
python3 scripts/render_report.py /percorso/ristoranti.json /percorso/ristoranti.html
```

Controlla report, fonti, confini, marker e corrispondenza schede. Consegna link cliccabile al file e indica miglior proposta e maggiore incertezza.

HTML funziona senza JavaScript per contenuto e classifica. Mappa richiede rete e anteprima HTTP:

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory /percorso/restaurant-reports/<zona>-<data>
```

Apri `http://127.0.0.1:8765/ristoranti.html`. Servi solo cartella report. Non pubblicare dati o avviare server pubblico.
