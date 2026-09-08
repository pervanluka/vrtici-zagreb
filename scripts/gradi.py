"""Spaja otvorene kontakt-skupove Grada sa zadnjim snapshotom slobodnih mjesta
i proizvodi statični JSON koji čita stranica.

Pokretanje: python3 scripts/gradi.py
"""

import csv
import json
import re
import sys
import unicodedata
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
SNAPSHOTI = KORIJEN / "data" / "slobodna-mjesta"
IZNIMKE = KORIJEN / "data" / "iznimke.csv"
IZLAZ = KORIJEN / "site" / "data"

KONTAKT_SKUPOVI = {
    "gradski": (
        "https://data.zagreb.hr/dataset/10f10ce2-44a0-4a2c-96f5-249f218b3d21"
        "/resource/ef3f6fc2-d648-4dba-a7b2-f7e8990d8cd0/download/data.json"
    ),
    "privatni": (
        "https://data.zagreb.hr/dataset/25a37ebd-13af-4979-8b50-4c081a6b9386"
        "/resource/8fa8e3b5-7a3b-4b75-98a4-0743b29f79bc/download/data.json"
    ),
}

# Ispod ovoga je normalizacija naziva vjerojatno pukla, a ne skup podataka
# promijenjen. Radije pasti nego objaviti kartu bez pinova.
PRAG_SPOJENOSTI = 0.90


def _bez_dijakritika(tekst):
    return "".join(
        z for z in unicodedata.normalize("NFD", tekst) if unicodedata.category(z) != "Mn"
    )


def normaliziraj_naziv(naziv):
    """Naziv iz bilo kojeg izvora → zajednički ključ ustanove.

    'DJEČJI VRTIĆ BAJKA', 'DV Bajka-matični objekt' i 'DV Bajka-PO Humska'
    daju isti ključ, jer su slobodna mjesta uvijek na razini matične ustanove.
    """
    k = _bez_dijakritika(naziv).upper()
    k = k.replace("DJECJI VRTIC ", "DV ")
    k = re.sub(r"\s*-\s*(MATICNI OBJEKT|PO\b.*)$", "", k)
    k = re.sub(r"[^A-Z0-9 ]", " ", k)
    return " ".join(k.split())


def kljuc_cetvrti(cetvrt):
    k = _bez_dijakritika(cetvrt).upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", k).split())


def ucitaj_iznimke(put=IZNIMKE):
    """CSV s dva stupca: naziv_tablica,naziv_kontakt → mapa normaliziranih ključeva."""
    if not put.exists():
        return {}
    with put.open(encoding="utf-8", newline="") as f:
        return {
            normaliziraj_naziv(red["naziv_tablica"]): normaliziraj_naziv(red["naziv_kontakt"])
            for red in csv.DictReader(f)
            if red.get("naziv_tablica") and red.get("naziv_kontakt")
        }


def dohvati_kontakte():
    kontakti = []
    for url in KONTAKT_SKUPOVI.values():
        zahtjev = urllib.request.Request(url, headers={"User-Agent": "vrtici-zagreb/1.0"})
        with urllib.request.urlopen(zahtjev, timeout=60) as odgovor:
            kontakti.extend(json.load(odgovor))
    return kontakti


def _objekt(k):
    return {
        "naziv": k["Naziv"],
        "tip": k.get("TipVrtica") or "",
        "adresa": k.get("Adresa") or "",
        "telefon": k.get("Telefon") or "",
        "email": k.get("Email") or "",
        "web": k.get("Web") or "",
        "x": float(k["X"].replace(",", ".")),
        "y": float(k["Y"].replace(",", ".")),
    }


def spoji(retci, kontakti, iznimke):
    """Retci snapshota + kontakti → lista ustanova, i popis nespojenih naziva."""
    po_kljucu = {}
    for k in kontakti:
        if not k.get("X") or not k.get("Y"):
            continue
        po_kljucu.setdefault(normaliziraj_naziv(k["Naziv"]), []).append(k)

    ustanove, redoslijed = {}, []
    for red in retci:
        kljuc = normaliziraj_naziv(red["naziv"])
        kljuc_kontakta = iznimke.get(kljuc, kljuc)
        if kljuc not in ustanove:
            ustanove[kljuc] = {
                "kljuc": kljuc,
                "naziv": red["naziv"],
                "vrsta": red["vrsta"],
                "cetvrt": red["cetvrt"],
                "kljuc_cetvrti": kljuc_cetvrti(red["cetvrt"]),
                "slobodnih_ukupno": 0,
                "mjesta": [],
                "objekti": [_objekt(k) for k in po_kljucu.get(kljuc_kontakta, [])],
            }
            redoslijed.append(kljuc)
        u = ustanove[kljuc]
        slobodnih = int(red["slobodnih"])
        u["slobodnih_ukupno"] += slobodnih
        u["mjesta"].append(
            {
                "dobna_skupina": red["dobna_skupina"],
                "uzrast": red["uzrast"],
                "program": red["program"],
                "slobodnih": slobodnih,
            }
        )

    popis = [ustanove[k] for k in redoslijed]
    nespojeni = [u["naziv"] for u in popis if not u["objekti"]]
    return popis, nespojeni


def zadnji_snapshot():
    snapshotovi = sorted(
        p for p in SNAPSHOTI.glob("*.csv") if p.name != "serija.csv"
    )
    if not snapshotovi:
        raise FileNotFoundError(
            "nema nijednog snapshota — pokreni prvo: python3 scripts/prikupi.py"
        )
    return snapshotovi[-1]


def main():
    put = zadnji_snapshot()
    datum_stanja = date.fromisoformat(put.stem)
    with put.open(encoding="utf-8", newline="") as f:
        retci = list(csv.DictReader(f))

    ustanove, nespojeni = spoji(retci, dohvati_kontakte(), ucitaj_iznimke())

    udio = 1 - len(nespojeni) / len(ustanove)
    print(f"spojeno {len(ustanove) - len(nespojeni)}/{len(ustanove)} ustanova ({udio:.0%})")
    for naziv in nespojeni:
        print(f"  bez koordinata: {naziv}")
    if udio < PRAG_SPOJENOSTI:
        raise ValueError(
            f"spojeno samo {udio:.0%}, prag je {PRAG_SPOJENOSTI:.0%} — "
            "provjeri normaliziraj_naziv() ili dopuni data/iznimke.csv"
        )

    IZLAZ.mkdir(parents=True, exist_ok=True)
    (IZLAZ / "ustanove.json").write_text(
        json.dumps(
            {
                "datum_stanja": datum_stanja.isoformat(),
                "generirano": datetime.now(timezone.utc).date().isoformat(),
                "izvor": "Grad Zagreb",
                "ustanove": ustanove,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    print(f"zapisano → {(IZLAZ / 'ustanove.json').relative_to(KORIJEN)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as greska:  # noqa: BLE001
        print(f"GREŠKA: {greska}", file=sys.stderr)
        sys.exit(1)
