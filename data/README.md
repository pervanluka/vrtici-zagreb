# Skup podataka: slobodna mjesta u zagrebačkim vrtićima

Licenca: **CC-BY 4.0**. Izvor podataka: **Grad Zagreb**.

Podaci o slobodnim mjestima prikupljeni su sa stranice
<https://vrtici.zagreb.hr/slobodna-mjesta/187>, koja ih objavljuje mjesečno
i pritom **prepisuje prethodni mjesec**. Ovaj repozitorij čuva svaku snimku,
pa nastaje vremenska serija koja inače ne postoji.

Kontakt podaci ustanova preuzimaju se s portala otvorenih podataka
Grada Zagreba (<https://data.zagreb.hr>), pod Otvorenom dozvolom.

## Shema

`datum_stanja,naziv,vrsta,cetvrt,dobna_skupina,uzrast,program,slobodnih`

## Snimke

| Datum stanja | Redaka | Slobodnih mjesta | Pokriveno |
|---|---|---|---|
| 2023-03-01 | 970 | 83 | Gradski DV, Privatni i vjerski DV |
| 2025-01-01 | 894 | 187 | Gradski DV, Obrt dadilja |
| 2026-09-01 | 1030 | 1237 | Gradski DV, Obrt dadilja, Privatni i vjerski DV |
| 2026-10-01 | 1030 | 1012 | Gradski DV, Obrt dadilja, Privatni i vjerski DV |

## Ograničenja

- Slobodna mjesta su na razini **matične ustanove**, ne pojedinog objekta.
- Snimka iz 2025. ne pokriva privatne i vjerske vrtiće; ona iz 2023. ne pokriva obrte dadilja.
- Snimke su iz različitih mjeseci u godini (ožujak, siječanj, rujan), pa uz različit
  obuhvat vrsta ustanova nisu izravno usporedive: dio razlike između njih dolazi od
  toga što ranija snimka nije mjerila neku vrstu ustanove, a ne od stvarne promjene
  broja mjesta.
- Gradska četvrt Brezovica ima ustanove, ali se ni u jednoj snimci slobodnih mjesta ne pojavljuje.
- Ista je četvrt u izvorima pisana različito; u izvedenim prikazima svodi se na jedan naziv.
- Snimka iz 2023. bilježi nazive ustanova onako kako ih izvor piše — bez prefiksa
  `DV` / `DAD` koji nose snimke iz 2025. i 2026. Zato se nazivi ustanova ne mogu
  izravno uspoređivati između snimaka. Zbrajanje po gradskoj četvrti i po vrsti
  ustanove, na kojem počivaju svi prikazi vremenske serije, time nije pogođeno.
- Podatak je mjesečna snimka, ne stanje uživo.

## Kako je koja snimka provjerena

Snimka od 2026-09-01 — i svaka sljedeća — nastaje skriptom `scripts/prikupi.py`,
koja prije zapisa usporedi zbroj parsiranih redaka s osam kontrolnih brojki koje
izvorna stranica sama objavljuje (ukupno, po vrsti ustanove i po dobnoj skupini).
Ako se ne poklope, snimka se ne zapisuje.

Snimke od 2023-03-01 i 2025-01-01 prevedene su iz zamrznutih portalskih skupova
skriptom `scripts/povijest.py`, koja tu provjeru **ne radi automatski**. Ti skupovi
kontrolne brojke nose u zbirnim retcima i stupcima (`UKUPNO`, `SVEUKUPNO`), a skripta
ih preskače da se mjesta ne bi brojala dvaput. Njihovi su zbrojevi provjereni ručnim
prebrojavanjem prema tim zbirnim retcima izvora: 2023-03-01 daje 51 (gradski) + 32
(privatni i vjerski) = 83 mjesta, a 2025-01-01 daje 174 (gradski) + 13 (dadilje) =
187 mjesta. Oba su skupa zamrznuta i više se ne mijenjaju.
