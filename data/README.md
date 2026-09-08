# Skup podataka: slobodna mjesta u zagrebačkim vrtićima

Licenca: **CC-BY 4.0**. Izvor podataka: **Grad Zagreb**.

Podaci o slobodnim mjestima prikupljeni su sa stranice
<https://vrtici.zagreb.hr/slobodna-mjesta/187>, koja ih objavljuje mjesečno
i pritom **prepisuje prethodni mjesec**. Ovaj repozitorij čuva svaki snimak,
pa nastaje vremenska serija koja inače ne postoji.

Kontakt podaci ustanova preuzimaju se s portala otvorenih podataka
Grada Zagreba (<https://data.zagreb.hr>), pod Otvorenom dozvolom.

## Shema

`datum_stanja,naziv,vrsta,cetvrt,dobna_skupina,uzrast,program,slobodnih`

## Snapshotovi

| Datum stanja | Redaka | Slobodnih mjesta | Pokriveno |
|---|---|---|---|
| 2023-03-01 | 970 | 83 | Gradski DV, Privatni i vjerski DV |
| 2025-01-01 | 894 | 187 | Gradski DV, Obrt dadilja |
| 2026-09-01 | 1030 | 1237 | Gradski DV, Obrt dadilja, Privatni i vjerski DV |

## Ograničenja

- Slobodna mjesta su na razini **matične ustanove**, ne pojedinog objekta.
- Snapshot iz 2025. ne pokriva privatne i vjerske vrtiće; onaj iz 2023. ne pokriva obrte dadilja.
- Gradska četvrt Brezovica ima ustanove, ali se ni u jednoj snimci slobodnih mjesta ne pojavljuje.
- Ista četvrt je u izvorima pisana različito; u izvedenim prikazima svodi se na jedan naziv.
- Podatak je mjesečni snimak, ne stanje uživo.

Svaki snapshot proizveden je skriptom `scripts/prikupi.py` (odnosno
`scripts/povijest.py` za 2023. i 2025.), a prije zapisa provjereno je da se
zbroj redaka poklapa s kontrolnim brojkama koje izvor sam objavljuje.
