# Slobodna mjesta u zagrebačkim vrtićima

Karta, pretraživač i otvoreni skup podataka o slobodnim upisnim mjestima u
ustanovama za rani i predškolski odgoj u Gradu Zagrebu.

Grad Zagreb objavljuje broj slobodnih mjesta mjesečno i pritom prepisuje
prethodni mjesec — povijest se ne čuva. Ovaj projekt svaku snimku sprema i
objavljuje kao otvoreni podatak, pa nastaje vremenska serija koja inače ne
postoji.

## Pokretanje

Potreban je samo Python 3.11+. Nema vanjskih ovisnosti.

```bash
python3 scripts/prikupi.py    # dohvati novu snimku (ako je ima)
python3 scripts/gradi.py      # spoji podatke i generiraj site/data/
python3 -m http.server 8000 --directory site
```

Snimke iz 2023. i 2025. već su uključene (vidi `data/slobodna-mjesta/`). Ako
ih trebate ponovno dohvatiti, pokrenite `python3 scripts/povijest.py` — to je
jednokratni korak, koji je izvršen kad su povijesne snimke dodane u repozitorij.
**Skripta bez pitanja prepisuje** `data/slobodna-mjesta/2023-03-01.csv`,
`2025-01-01.csv` i `serija.csv`.

## Testovi

```bash
python3 -m unittest discover -s tests -v
```

## Struktura

| Putanja | Sadržaj |
|---|---|
| `data/` | javni skup podataka (CC-BY 4.0) |
| `scripts/parsiranje.py` | čiste funkcije: HTML → retci, zbrojevi, datum |
| `scripts/prikupi.py` | dohvat, provjera kontrolnih zbrojeva, zapis snimke |
| `scripts/povijest.py` | mrtvi skupovi 2023./2025. → kanonska shema |
| `scripts/gradi.py` | spajanje s kontakt-skupovima → `site/data/` |
| `scripts/provenijencija.py` | tablica snimaka → `data/README.md` |
| `scripts/iznimke.csv` | ručni ispravci naziva za spajanje (ulaz za kod, ne dio skupa) |
| `site/` | statična stranica |

## Licence

Kod: MIT (Luka Pervan). Podaci: CC-BY 4.0, izvor Grad Zagreb. Treće strane
(`site/vendor/`): BSD-2-Clause (Leaflet). Vidi `data/README.md` za
provenijenciju svake snimke.
