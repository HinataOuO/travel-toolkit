# Travel Toolkit

Raccolta di skill Codex per organizzare vacanze e scegliere dove mangiare.

## Skill incluse

- `vacation-planner`: crea alternative di viaggio, itinerari, budget e report HTML.
- `restaurant-finder`: confronta locali e genera classifiche e report HTML.

## Installazione in Codex

Rendi eseguibile e avvia `install-skills.sh`. Su un file manager configurato per
eseguire gli script basta fare doppio clic. Da terminale:

```sh
./install-skills.sh
```

Lo script crea i collegamenti in `${CODEX_HOME:-$HOME/.codex}/skills`. Può essere
eseguito più volte. Se trova un file o una directory reale con lo stesso nome,
si ferma senza sovrascriverla.
