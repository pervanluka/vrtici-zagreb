"""Parsiranje stranice vrtici.zagreb.hr/slobodna-mjesta.

Sve funkcije su čiste: primaju HTML kao string i ne dodiruju ni mrežu ni disk.
Zato se testiraju nad zamrznutim fixtureom, bez mocka.
"""

import html as _html
import re
from datetime import date

MJESECI = {
    "siječnja": 1,
    "veljače": 2,
    "ožujka": 3,
    "travnja": 4,
    "svibnja": 5,
    "lipnja": 6,
    "srpnja": 7,
    "kolovoza": 8,
    "rujna": 9,
    "listopada": 10,
    "studenog": 11,
    "prosinca": 12,
}

STUPCI = ["naziv", "vrsta", "cetvrt", "dobna_skupina", "uzrast", "program", "slobodnih"]

# Stranica uz tablicu ispisuje i kontrolne zbrojeve u tekstu. Oni su jedina
# obrana od tihe promjene HTML-a, pa se čitaju i uspoređuju sa zbrojem redaka.
# \D{0,12} preskače interpunkciju između fraza ("vrtićima , od čega").
_ZBROJEVI = {
    "ukupno": r"slobodno je ([\d.]+) upisnih mjesta",
    "gradski": r"([\d.]+) u gradskim vrtićima",
    "gradski_jaslice": r"u gradskim vrtićima\D{0,12}od čega ([\d.]+) jasličkih",
    "gradski_vrtic": r"u gradskim vrtićima\D{0,12}od čega [\d.]+ jasličkih te ([\d.]+) vrtićkih",
    "privatni": r"([\d.]+) u privatnim i vjerskim vrtićima",
    "privatni_jaslice": r"u privatnim i vjerskim vrtićima\D{0,12}od čega ([\d.]+) jasličkih",
    "privatni_vrtic": (
        r"u privatnim i vjerskim vrtićima\D{0,12}od čega [\d.]+ jasličkih te ([\d.]+) vrtićkih"
    ),
    "dadilje": r"([\d.]+) u obrtima dadilja",
}


def tekst(dokument):
    """HTML → ravni tekst s normaliziranim razmacima."""
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", dokument)).split())


def parse_datum(dokument, danas):
    """'Na dan 1. rujna' → date(2026, 9, 1).

    Stranica ne navodi godinu, pa se izvodi iz `danas`. Ako je u siječnju
    prikazano prosinačko stanje, godina je prethodna.
    """
    uzorak = r"Na dan (\d{1,2})\.\s*(" + "|".join(MJESECI) + r")"
    m = re.search(uzorak, tekst(dokument))
    if not m:
        raise ValueError("datum stanja nije pronađen na stranici")
    dan, mjesec = int(m.group(1)), MJESECI[m.group(2)]
    godina = danas.year - 1 if (mjesec == 12 and danas.month == 1) else danas.year
    return date(godina, mjesec, dan)


def parse_zbrojeve(dokument):
    """Kontrolni zbrojevi iz uvodnog teksta stranice."""
    t = tekst(dokument)
    zbrojevi = {}
    for kljuc, uzorak in _ZBROJEVI.items():
        m = re.search(uzorak, t)
        if not m:
            raise ValueError(f"kontrolni zbroj '{kljuc}' nije pronađen na stranici")
        zbrojevi[kljuc] = int(m.group(1).replace(".", ""))
    return zbrojevi


def parse_retke(dokument):
    """Tablica slobodnih mjesta → lista dictova sa ključevima iz STUPCI."""
    retci = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", dokument, re.S):
        celije = [
            " ".join(_html.unescape(re.sub(r"<[^>]+>", "", c)).split())
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        ]
        if len(celije) != len(STUPCI) or not celije[-1].isdigit():
            continue  # zaglavlje i sve što nije redak s brojem
        red = dict(zip(STUPCI, celije))
        red["slobodnih"] = int(red["slobodnih"])
        retci.append(red)
    if not retci:
        raise ValueError("tablica slobodnih mjesta nije pronađena")
    return retci
