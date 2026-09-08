"""Tjedni obilazak stranice sa slobodnim mjestima.

Ako se datum stanja nije promijenio, skripta ne radi ništa. Ako jest,
parsira tablicu, provjeri zbrojeve i zapiše novi snapshot.

Pokretanje: python3 scripts/prikupi.py
Izlazni kod 0 = nema promjene ili uspješan zapis, 1 = greška.
"""

import csv
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import parsiranje

IZVOR = "https://vrtici.zagreb.hr/slobodna-mjesta/187"
KORIJEN = Path(__file__).resolve().parent.parent
SNAPSHOTI = KORIJEN / "data" / "slobodna-mjesta"
ZAGLAVLJE = ["datum_stanja"] + parsiranje.STUPCI

GRADSKI = "Gradski DV"
PRIVATNI = "Privatni i vjerski DV"
DADILJE = "Obrt dadilja"


def dohvati(url=IZVOR):
    zahtjev = urllib.request.Request(url, headers={"User-Agent": "vrtici-zagreb/1.0"})
    with urllib.request.urlopen(zahtjev, timeout=60) as odgovor:
        return odgovor.read().decode("utf-8", errors="replace")


def provjeri_zbrojeve(retci, zbrojevi):
    """Usporedi zbroj parsiranih redaka s kontrolnim brojkama sa stranice.

    Ovo je jedina obrana od tihe promjene HTML-a. Neslaganje znači da parser
    više ne vidi cijelu tablicu — bolje pasti nego objaviti krive brojke.
    """

    def zbroj(**uvjeti):
        return sum(
            r["slobodnih"] for r in retci if all(r[k] == v for k, v in uvjeti.items())
        )

    izracunato = {
        "ukupno": sum(r["slobodnih"] for r in retci),
        "gradski": zbroj(vrsta=GRADSKI),
        "gradski_jaslice": zbroj(vrsta=GRADSKI, dobna_skupina="Jaslice"),
        "gradski_vrtic": zbroj(vrsta=GRADSKI, dobna_skupina="Vrtić"),
        "privatni": zbroj(vrsta=PRIVATNI),
        "privatni_jaslice": zbroj(vrsta=PRIVATNI, dobna_skupina="Jaslice"),
        "privatni_vrtic": zbroj(vrsta=PRIVATNI, dobna_skupina="Vrtić"),
        "dadilje": zbroj(vrsta=DADILJE),
    }
    odstupanja = {
        k: {"izracunato": izracunato[k], "stranica": v}
        for k, v in zbrojevi.items()
        if izracunato[k] != v
    }
    if odstupanja:
        raise ValueError(f"zbrojevi se ne poklapaju sa stranicom: {odstupanja}")
    return izracunato


def zadnji_snapshot(mapa=SNAPSHOTI):
    datumi = []
    for put in mapa.glob("*.csv"):
        try:
            datumi.append(date.fromisoformat(put.stem))
        except ValueError:
            continue  # serija.csv i slično
    return max(datumi) if datumi else None


def zapisi_snapshot(mapa, datum_stanja, retci):
    mapa.mkdir(parents=True, exist_ok=True)
    put = mapa / f"{datum_stanja.isoformat()}.csv"
    with put.open("w", encoding="utf-8", newline="") as f:
        pisac = csv.DictWriter(f, fieldnames=ZAGLAVLJE, lineterminator="\n")
        pisac.writeheader()
        for red in retci:
            pisac.writerow({"datum_stanja": datum_stanja.isoformat(), **red})
    return put


def obnovi_seriju(mapa=SNAPSHOTI):
    put = mapa / "serija.csv"
    with put.open("w", encoding="utf-8", newline="") as f:
        pisac = csv.DictWriter(f, fieldnames=ZAGLAVLJE, lineterminator="\n")
        pisac.writeheader()
        for snapshot in sorted(mapa.glob("*.csv")):
            if snapshot.name == "serija.csv":
                continue
            with snapshot.open(encoding="utf-8", newline="") as ulaz:
                pisac.writerows(csv.DictReader(ulaz))
    return put


def main():
    dokument = dohvati()
    danas = datetime.now(timezone.utc).date()
    datum_stanja = parsiranje.parse_datum(dokument, danas)

    if datum_stanja == zadnji_snapshot():
        print(f"nema promjene — stranica i dalje prikazuje stanje {datum_stanja}")
        return 0

    retci = parsiranje.parse_retke(dokument)
    zbrojevi = parsiranje.parse_zbrojeve(dokument)
    izracunato = provjeri_zbrojeve(retci, zbrojevi)

    put = zapisi_snapshot(SNAPSHOTI, datum_stanja, retci)
    obnovi_seriju()
    print(
        f"nov snapshot {datum_stanja}: {len(retci)} redaka, "
        f"{izracunato['ukupno']} slobodnih mjesta → {put.relative_to(KORIJEN)}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as greska:  # noqa: BLE001 — CI treba vidjeti poruku, ne stack
        print(f"GREŠKA: {greska}", file=sys.stderr)
        sys.exit(1)
