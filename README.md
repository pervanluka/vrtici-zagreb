# Slobodna mjesta u zagrebačkim vrtićima

Karta, pretraživač i otvoreni skup podataka o slobodnim upisnim mjestima u
ustanovama za rani i predškolski odgoj u Gradu Zagrebu.

Grad Zagreb objavljuje broj slobodnih mjesta mjesečno i pritom prepisuje
prethodni mjesec — povijest se ne čuva. Ovaj projekt svaki snimak sprema i
objavljuje kao otvoreni podatak, pa nastaje vremenska serija koja inače ne
postoji.

## Pokretanje

Potreban je samo Python 3.11+. Nema vanjskih ovisnosti.

```bash
python3 scripts/prikupi.py    # dohvati novi snimak (ako ga ima)
python3 scripts/povijest.py   # jednokratno: snapshotovi 2023. i 2025.
python3 scripts/gradi.py      # spoji podatke i generiraj site/data/
python3 -m http.server 8000 --directory site
```

## Testovi

```bash
python3 -m unittest discover -s tests -v
```

## Struktura

| Putanja | Sadržaj |
|---|---|
| `data/` | javni skup podataka (CC-BY 4.0) |
| `scripts/parsiranje.py` | čiste funkcije: HTML → retci, zbrojevi, datum |
| `scripts/prikupi.py` | dohvat, provjera kontrolnih zbrojeva, zapis snimka |
| `scripts/povijest.py` | mrtvi skupovi 2023./2025. → kanonska shema |
| `scripts/gradi.py` | spajanje s kontakt-skupovima → `site/data/` |
| `site/` | statična stranica |

## Licence

Kod: MIT. Podaci: CC-BY 4.0, izvor Grad Zagreb. Vidi `data/README.md` za
provenijenciju svakog snimka.
