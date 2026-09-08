"""Prevodi mrtve skupove s data.zagreb.hr (stanja 1.3.2023. i 1.1.2025.)
u istu kanonsku shemu kao živi izvor, da vremenska serija ima povijesna sidra.

2025. skup je u wide obliku s troredim zaglavljem: prvi red nosi dobnu
skupinu (JASLICE / VRTIĆ), drugi uzrast, treći program. 2023. gradski skup
je *također* wide, ali s jednorednim zaglavljem — dobna skupina, uzrast i
program su spojeni u jednu ćeliju po stupcu (npr. "JASLICE od 1 do 2 godine
REDOVITI PROGRAM"), pa treba zaseban parser (parse_gradski_2023). 2023.
privatni/vjerski skup ne razlaže mjesta po uzrastu/programu uopće — nosi
samo zbroj po dobnoj skupini (parse_privatni_2023).

Stupci UKUPNO/SVEUKUPNO (zbirni redci i stupci) se svugdje preskaču jer bi
se inače brojali dvaput.

Pokretanje: python3 scripts/povijest.py
"""

import csv
import io
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

import prikupi

KORIJEN = Path(__file__).resolve().parent.parent

SKUPOVI = {
    date(2023, 3, 1): {
        "Gradski DV": (
            "https://data.zagreb.hr/dataset/63190e2c-93c6-419e-868d-ac2e09169d9f"
            "/resource/fa300c6d-d4ac-4711-83cc-de4045df3a50/download/"
            "podaci-o-slobodnim-mjestima-u-gradskim-vrticima-2022.-2023.-01.03.2023.csv"
        ),
        "Privatni i vjerski DV": (
            "https://data.zagreb.hr/dataset/63190e2c-93c6-419e-868d-ac2e09169d9f"
            "/resource/57b832eb-2a67-4529-bd04-13cf9a14768f/download/"
            "podaci-o-slobodnim-mjestima-u-privatnim-i-vjerskim-vrticima-na-dan-01.03.2023.-1.csv"
        ),
    },
    date(2025, 1, 1): {
        "Gradski DV": (
            "https://data.zagreb.hr/dataset/2286de51-f7bf-45ae-a212-9a5530527c94"
            "/resource/a6a9199d-eaf4-4f75-9bce-7a3a5b367d30/download/"
            "slobodna-mjesta-u-gradskim-dv-01.01.2025..csv"
        ),
        "Obrt dadilja": (
            "https://data.zagreb.hr/dataset/2286de51-f7bf-45ae-a212-9a5530527c94"
            "/resource/f1c42d5e-17c8-40e9-83a9-fba7539bd4b5/download/"
            "slobodna-mjesta-dadilje-1.1.25-csv.csv"
        ),
    },
}

# Živi izvor piše "4 do 5 godina"; skupovi iz 2023./2025. pišu "4 do 5 godine".
# Bez ovog ispravka isti uzrast bi u seriji bio dvije različite kategorije.
UZRAST_ISPRAVCI = {"4 do 5 godine": "4 do 5 godina"}

DOBNE = {"JASLICE": "Jaslice", "VRTIĆ": "Vrtić"}
PROGRAMI = {"REDOVITI PROGRAM": "Redoviti", "POSEBNI PROGRAM": "Posebni"}

# Redci koje treba preskočiti — zbirni redak na dnu izvještaja (naziv ustanove
# je "UKUPNO"/"SVEUKUPNO" umjesto stvarnog naziva).
ZBIRNI_NAZIVI = {"UKUPNO", "SVEUKUPNO"}


def ocisti_uzrast(vrijednost):
    u = " ".join(vrijednost.replace("(", " ").replace(")", " ").split())
    if u.lower().startswith("od "):
        u = u[3:]
    return UZRAST_ISPRAVCI.get(u, u)


def naprijed(redak):
    """Forward-fill: prazna ćelija preuzima zadnju nepraznu lijevo od sebe."""
    popunjen, zadnja = [], ""
    for celija in redak:
        if celija.strip():
            zadnja = celija.strip()
        popunjen.append(zadnja)
    return popunjen


def stupci_mjesta(r1, r2, r3):
    """Iz troredog zaglavlja (2025.) izvuci (indeks, dobna_skupina, uzrast, program)."""
    dobne, uzrasti = naprijed(r1), naprijed(r2)
    stupci = []
    for i in range(3, len(r3)):
        program = PROGRAMI.get(r3[i].strip().upper())
        if not program:
            continue  # UKUPNO RED. + POS. i prazni stupci
        if uzrasti[i].strip().upper().startswith("UKUPNO"):
            continue  # zbirni stupac — brojao bi se dvaput
        dobna = DOBNE.get(dobne[i].strip().upper())
        if not dobna:
            continue
        stupci.append((i, dobna, ocisti_uzrast(uzrasti[i]), program))
    return stupci


def stupci_2023(header):
    """Iz jednorednog zaglavlja (2023. gradski) izvuci (indeks, dobna, uzrast, program).

    Format se ovdje razlikuje od 2025.: dobna skupina, uzrast i program su
    spojeni u JEDNU ćeliju po stupcu ("JASLICE od 1 do 2 godine REDOVITI
    PROGRAM"), a poneki razmak i nedostaje (npr. "OŠREDOVITI PROGRAM") —
    zato se traži podniz "REDOVITI"/"POSEBNI", a ne razdvaja po razmaku.
    """
    stupci = []
    for i, celija in enumerate(header):
        sirovo = celija.strip()
        gornje = sirovo.upper()
        if gornje.startswith("JASLICE"):
            dobna, ostatak = "Jaslice", sirovo[len("JASLICE"):]
        elif gornje.startswith("VRTIĆ"):
            dobna, ostatak = "Vrtić", sirovo[len("VRTIĆ"):]
        else:
            continue  # naziv, četvrt, prazni prateći stupci
        ostatak_gornje = ostatak.upper()
        if "POSEBNI" in ostatak_gornje:
            program, kraj = "Posebni", ostatak_gornje.index("POSEBNI")
        elif "REDOVITI" in ostatak_gornje:
            program, kraj = "Redoviti", ostatak_gornje.index("REDOVITI")
        else:
            continue
        sirovi_uzrast = ostatak[:kraj].strip()
        if sirovi_uzrast.upper() == "UKUPNO":
            continue  # zbirni stupac po dobnoj skupini — brojao bi se dvaput
        stupci.append((i, dobna, ocisti_uzrast(sirovi_uzrast), program))
    return stupci


def _bez_biljeske(cetvrt):
    """Skine bilješku o područnim objektima u drugim četvrtima, npr.
    "DONJI GRAD (*Gornji grad-Medveščak; Podsljeme)" → "DONJI GRAD"."""
    return re.sub(r"\s*\(.*\)\s*$", "", cetvrt.strip()).strip()


def _bez_zvjezdica(naziv):
    """Skine bilješku o područnom objektu iz naziva ustanove, npr.
    "Različak *" → "Različak"."""
    return re.sub(r"\*+\s*$", "", naziv.strip()).strip()


def _citac(tekst):
    return list(csv.reader(io.StringIO(tekst.lstrip("﻿")), delimiter=";"))


def parse_gradski_wide(tekst, vrsta):
    """2025. gradski/dadiljski wide skup s troredim zaglavljem."""
    redovi = _citac(tekst)
    if len(redovi) < 4:
        raise ValueError("wide CSV nema očekivano trorede zaglavlje")
    stupci = stupci_mjesta(redovi[0], redovi[1], redovi[2])
    if not stupci:
        raise ValueError("u zaglavlju nije prepoznat nijedan stupac s mjestima")

    retci, cetvrt = [], ""
    for red in redovi[3:]:
        if len(red) < 3 or not red[1].strip():
            continue
        cetvrt = red[0].strip() or cetvrt
        naziv = red[1].strip()
        for i, dobna, uzrast, program in stupci:
            vrijednost = red[i].strip() if i < len(red) else ""
            if not vrijednost.isdigit():
                continue
            retci.append(
                {
                    "naziv": naziv,
                    "vrsta": vrsta,
                    "cetvrt": cetvrt,
                    "dobna_skupina": dobna,
                    "uzrast": uzrast,
                    "program": program,
                    "slobodnih": int(vrijednost),
                }
            )
    return retci


def parse_gradski_2023(tekst, vrsta):
    """2023. gradski skup: jednoredno zaglavlje (vidi stupci_2023).

    Podaci su inače istog oblika kao 2025.: četvrt se forward-filla, a na
    dnu je zbirni redak ("UKUPNO") koji treba preskočiti — ovdje mu naziv
    ustanove NIJE prazan (za razliku od 2025. formata), pa ga se mora
    prepoznati eksplicitno po nazivu.
    """
    redovi = _citac(tekst)
    if len(redovi) < 2:
        raise ValueError("2023. gradski CSV nema očekivano zaglavlje")
    stupci = stupci_2023(redovi[0])
    if not stupci:
        raise ValueError("u zaglavlju nije prepoznat nijedan stupac s mjestima")

    retci, cetvrt = [], ""
    for red in redovi[1:]:
        if len(red) < 2 or not red[1].strip():
            continue  # naslovni redak na dnu nema naziv
        naziv = _bez_zvjezdica(red[1])
        if naziv.upper() in ZBIRNI_NAZIVI:
            continue  # zbirni redak na dnu izvještaja
        cetvrt = _bez_biljeske(red[0]) or cetvrt
        for i, dobna, uzrast, program in stupci:
            vrijednost = red[i].strip() if i < len(red) else ""
            if not vrijednost.isdigit():
                continue
            retci.append(
                {
                    "naziv": naziv,
                    "vrsta": vrsta,
                    "cetvrt": cetvrt,
                    "dobna_skupina": dobna,
                    "uzrast": uzrast,
                    "program": program,
                    "slobodnih": int(vrijednost),
                }
            )
    return retci


def parse_privatni_2023(tekst):
    """2023. privatni/vjerski skup: samo zbroj po dobnoj skupini.

    Izvor ne daje raspodjelu po uzrastu ni programu (za razliku od gradskih
    vrtića), pa ta dva polja ostaju prazna — isto kao kod dadilja. Četvrt nosi
    istu bilješku o područnim objektima kao gradski skup (npr. "TRNJE (DONJI
    GRAD)"), pa se skida na isti način.
    """
    redovi = _citac(tekst)
    retci, cetvrt = [], ""
    for red in redovi[1:]:
        if len(red) < 4 or not red[1].strip():
            continue  # SVEUKUPNO i naslovni redak nemaju naziv
        naziv = _bez_zvjezdica(red[1])
        if naziv.upper() in ZBIRNI_NAZIVI:
            continue
        cetvrt = _bez_biljeske(red[0]) or cetvrt
        for indeks, dobna in ((2, "Jaslice"), (3, "Vrtić")):
            vrijednost = red[indeks].strip()
            if not vrijednost.isdigit():
                continue
            retci.append(
                {
                    "naziv": naziv,
                    "vrsta": "Privatni i vjerski DV",
                    "cetvrt": cetvrt,
                    "dobna_skupina": dobna,
                    "uzrast": "",
                    "program": "",
                    "slobodnih": int(vrijednost),
                }
            )
    return retci


def parse_dadilje(tekst):
    """Skup dadilja je već uzak: četvrt, naziv, broj mjesta."""
    redovi = _citac(tekst)
    retci, cetvrt = [], ""
    for red in redovi[1:]:
        if len(red) < 4 or not red[2].strip():
            continue
        cetvrt = (red[1].strip() or red[0].strip()) or cetvrt
        broj = red[3].strip()
        if not broj.isdigit():
            continue
        retci.append(
            {
                "naziv": red[2].strip(),
                "vrsta": "Obrt dadilja",
                "cetvrt": cetvrt,
                "dobna_skupina": "",
                "uzrast": "",
                "program": "",
                "slobodnih": int(broj),
            }
        )
    return retci


def _parsiraj(datum_stanja, vrsta, tekst):
    """Bira parser za jedan izvorni skup.

    `Obrt dadilja` i `Privatni i vjerski DV` biraju se po vrsti, bez obzira na
    datum — svaka od tih vrsta dolazi iz točno jednog skupa i jednog oblika.
    Samo gradski skup ima dva oblika, pa se za njega gleda i datum: 2023. ima
    jednoredno zaglavlje, 2025. troredo.

    Ako bi neki budući skup donio npr. privatne vrtiće u obliku iz 2025.,
    dispatch po vrsti bi ga poslao u krivi parser — tada ovdje treba i datum.
    """
    if vrsta == "Obrt dadilja":
        return parse_dadilje(tekst)
    if vrsta == "Privatni i vjerski DV":
        return parse_privatni_2023(tekst)
    if datum_stanja == date(2023, 3, 1):
        return parse_gradski_2023(tekst, vrsta)
    return parse_gradski_wide(tekst, vrsta)


def dohvati(url):
    zahtjev = urllib.request.Request(url, headers={"User-Agent": "vrtici-zagreb/1.0"})
    with urllib.request.urlopen(zahtjev, timeout=60) as odgovor:
        sirovo = odgovor.read()
    for kodiranje in ("utf-8-sig", "cp1250"):
        try:
            return sirovo.decode(kodiranje)
        except UnicodeDecodeError:
            continue
    return sirovo.decode("utf-8", errors="replace")


def main():
    for datum_stanja, izvori in SKUPOVI.items():
        retci = []
        for vrsta, url in izvori.items():
            tekst = dohvati(url)
            dio = _parsiraj(datum_stanja, vrsta, tekst)
            print(f"  {datum_stanja} · {vrsta}: {len(dio)} redaka")
            retci.extend(dio)
        put = prikupi.zapisi_snapshot(prikupi.SNAPSHOTI, datum_stanja, retci)
        ukupno = sum(r["slobodnih"] for r in retci)
        print(f"{datum_stanja}: {len(retci)} redaka, {ukupno} mjesta → {put.relative_to(KORIJEN)}")
    prikupi.obnovi_seriju()
    print("serija.csv obnovljena")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as greska:  # noqa: BLE001
        print(f"GREŠKA: {greska}", file=sys.stderr)
        sys.exit(1)
