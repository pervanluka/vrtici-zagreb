"""Spaja otvorene kontakt-skupove Grada sa zadnjom snimkom slobodnih mjesta
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

import parsiranje
import prikupi
import provenijencija

KORIJEN = Path(__file__).resolve().parent.parent
SNAPSHOTI = KORIJEN / "data" / "slobodna-mjesta"
# ulaz za kod, ne dio objavljenog skupa — zato uz skripte, a ne pod data/
IZNIMKE = Path(__file__).resolve().parent / "iznimke.csv"
IZLAZ = KORIJEN / "site" / "data"
SERIJA = KORIJEN / "data" / "slobodna-mjesta" / "serija.csv"
# ista kanonska shema kao u prikupi.py — jedan izvor istine
ZAGLAVLJE = ["datum_stanja"] + parsiranje.STUPCI

ULAGANJA = {
    2023: ("https://opendata.arcgis.com/api/v3/datasets/"
           "e898521c36224b05b7bc0778632cd91d_0/downloads/data"
           "?format=geojson&spatialRefId=4326&where=1%3D1"),
    2024: ("https://hub.arcgis.com/api/v3/datasets/"
           "f1871e3fd952438e99dcccd63d37e81b_0/downloads/data"
           "?format=geojson&spatialRefId=4326&where=1%3D1"),
}

# Naziv polja s planiranim iznosom NIJE isti obrazac kroz godine — provjereno na
# stvarnim GeoJSON-ovima 8.9.2026.: 2023. piše "Plan2023" (puna godina, veliko P),
# 2024. piše "plan24" (skraćeno, malo p). Nema uzorka koji pogađa oboje.
POLJE_IZNOSA = {2023: "Plan2023", 2024: "plan24"}

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
    # skupovi kapitalnih ulaganja koriste zarez umjesto crtice i ponekad
    # dopisuju adresu iza naziva: 'DV "Medo Brundo", PO Novi Retkovec', 'DV "Bajka", Humska 1'
    k = re.sub(r"\s*,\s*.*$", "", k)
    k = re.sub(r"[^A-Z0-9 ]", " ", k)
    return " ".join(k.split())


def kljuc_cetvrti(cetvrt):
    k = _bez_dijakritika(cetvrt).upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", k).split())


def parse_ulaganja(geojson, godina):
    """GeoJSON kapitalnih ulaganja → samo predškolske ustanove, u obliku za kartu.

    Naziv polja s iznosom nije isti obrazac kroz godine (vidi POLJE_IZNOSA) — radije
    pasti na nepoznatoj godini nego tiho upisati iznos: None za skup koji stvarno ima
    taj podatak, samo pod drugim imenom polja.
    """
    if godina not in POLJE_IZNOSA:
        raise ValueError(
            f"nema poznatog polja s iznosom za godinu {godina} — provjeri stvarni "
            "naziv polja u GeoJSON-u i dopuni POLJE_IZNOSA"
        )
    polje = POLJE_IZNOSA[godina]
    ulaganja = []
    for f in geojson.get("features", []):
        sv = f.get("properties") or {}
        if (sv.get("Vrsta_objekta") or "").strip().upper() != "PREDŠKOLSKE USTANOVE":
            continue
        geom = f.get("geometry") or {}
        koord = geom.get("coordinates") or [None, None]
        sirovi_iznos = sv.get(polje)
        iznos = str(sirovi_iznos).strip() if sirovi_iznos is not None else ""
        ulaganja.append(
            {
                "godina": godina,
                "naziv": (sv.get("naziv") or "").strip(),
                "kljuc": normaliziraj_naziv(sv.get("naziv") or ""),
                "adresa": (sv.get("Adresa") or "").strip(),
                "opis_radova": (sv.get("Opis_radova") or "").strip(),
                "iznos": int(float(iznos)) if iznos else None,
                "x": float(koord[0]) if koord[0] is not None else None,
                "y": float(koord[1]) if koord[1] is not None else None,
                "spojena": None,  # popunjava pripoji_cetvrt() kad zna ključeve ustanova
                "cetvrt": None,
            }
        )
    return ulaganja


def pripoji_cetvrt(ulaganja, cetvrt_po_kljucu, iznimke):
    """Ulaganjima pripiše četvrt ustanove iz tablice slobodnih mjesta.

    Ide kroz istu mapu iznimaka kao spajanje kontakata (`spoji`) — isti naziv se
    ne smije normalizirati na dva mjesta po dva pravila.

    Nespojeno ulaganje NIJE dokaz da ustanova ne postoji, nego samo da joj naziv
    u ovom skupu nije pogođen; zato se polje zove `spojena`, a ne `postojeca`.
    Vraća nazive nespojenih ulaganja.
    """
    nespojena = []
    for u in ulaganja:
        kljuc = iznimke.get(u["kljuc"], u["kljuc"])
        u["spojena"] = kljuc in cetvrt_po_kljucu
        u["cetvrt"] = cetvrt_po_kljucu.get(kljuc)
        if not u["spojena"]:
            nespojena.append(u["naziv"])
    return nespojena


def ucitaj_iznimke(put=IZNIMKE):
    """CSV s dva stupca: naziv,zamjena → mapa normaliziranih ključeva.

    Jedna mapa za sva spajanja: i za kontakte i za ulaganja. Isti naziv ne smije
    imati dva različita ručna ispravka ovisno o tome koji ga spoj traži.
    """
    if not put.exists():
        return {}
    with put.open(encoding="utf-8", newline="") as f:
        return {
            normaliziraj_naziv(red["naziv"]): normaliziraj_naziv(red["zamjena"])
            for red in csv.DictReader(f)
            if red.get("naziv") and red.get("zamjena")
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
    """Retci snimke + kontakti → lista ustanova, i popis nespojenih naziva."""
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
            "nema nijedne snimke — pokreni prvo: python3 scripts/prikupi.py"
        )
    return snapshotovi[-1]


def agregiraj_seriju(retci):
    """serija.csv → zbrojevi po datumu, ukupno / po četvrti / po vrsti.

    Datum koji nema nijedan redak za neku kategoriju ostaje odsutan, a ne nula:
    snimka iz 2025. ne pokriva privatne vrtiće, i prikaz to mora razlikovati
    od stvarne nule.

    Gradske četvrti se svode na zajednički ključ prije zbrajanja — vidi komentar
    u tijelu funkcije.
    """
    ukupno, po_cetvrti, po_vrsti, datumi = {}, {}, {}, set()

    # Ista gradska četvrt piše se različito u različitim snimkama: izmjereno,
    # 36 različitih nizova za 16 stvarnih četvrti ("DONJI GRAD" / "Donji grad",
    # crtica vs. n-crtica). Bez svođenja na ključ trend po četvrti bi prikazao
    # dvije-tri nepovezane krivulje po četvrti umjesto jedne. Naziv za prikaz
    # uzima se iz najnovije snimke, jer to je pisanje koje korisnik vidi drugdje.
    naziv_cetvrti = {}
    for red in sorted(retci, key=lambda r: r["datum_stanja"]):
        naziv_cetvrti[kljuc_cetvrti(red["cetvrt"])] = red["cetvrt"]

    for red in retci:
        d = red["datum_stanja"]
        n = int(red["slobodnih"])
        cetvrt = naziv_cetvrti[kljuc_cetvrti(red["cetvrt"])]
        datumi.add(d)
        ukupno[d] = ukupno.get(d, 0) + n
        po_cetvrti.setdefault(cetvrt, {})
        po_cetvrti[cetvrt][d] = po_cetvrti[cetvrt].get(d, 0) + n
        po_vrsti.setdefault(red["vrsta"], {})
        po_vrsti[red["vrsta"]][d] = po_vrsti[red["vrsta"]].get(d, 0) + n
    return {
        "datumi": sorted(datumi),
        "ukupno": ukupno,
        "po_cetvrti": po_cetvrti,
        "po_vrsti": po_vrsti,
    }


def main():
    # serija.csv je izvedena datoteka: ako je mergean snimak koji je nastao prije
    # nje, zapisana serija ga ne sadrži. Obnavlja se iz mape snimaka prije čitanja,
    # da prikaz nikad ne ovisi o tome je li commitana kopija u koraku sa snimkama.
    prikupi.obnovi_seriju()

    put = zadnji_snapshot()
    datum_stanja = date.fromisoformat(put.stem)
    with put.open(encoding="utf-8", newline="") as f:
        retci = list(csv.DictReader(f))

    iznimke = ucitaj_iznimke()
    ustanove, nespojeni = spoji(retci, dohvati_kontakte(), iznimke)

    udio = 1 - len(nespojeni) / len(ustanove)
    print(f"spojeno {len(ustanove) - len(nespojeni)}/{len(ustanove)} ustanova ({udio:.0%})")
    for naziv in nespojeni:
        print(f"  bez koordinata: {naziv}")
    if udio < PRAG_SPOJENOSTI:
        raise ValueError(
            f"spojeno samo {udio:.0%}, prag je {PRAG_SPOJENOSTI:.0%} — "
            "provjeri normaliziraj_naziv() ili dopuni scripts/iznimke.csv"
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

    with SERIJA.open(encoding="utf-8", newline="") as f:
        serija = agregiraj_seriju(list(csv.DictReader(f)))
    (IZLAZ / "serija.json").write_text(
        json.dumps(serija, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    provenijencija.zapisi(provenijencija.sazetak_snimaka())
    print(f"serija: {len(serija['datumi'])} snimaka; data/README.md osvježen")

    cetvrt_po_kljucu = {u["kljuc"]: u["cetvrt"] for u in ustanove}
    svi = []
    for godina, url in ULAGANJA.items():
        zahtjev = urllib.request.Request(url, headers={"User-Agent": "vrtici-zagreb/1.0"})
        with urllib.request.urlopen(zahtjev, timeout=60) as odgovor:
            dio = parse_ulaganja(json.load(odgovor), godina)
        nespojena = pripoji_cetvrt(dio, cetvrt_po_kljucu, iznimke)
        print(f"ulaganja {godina}: {len(dio)} predškolskih, "
              f"{len(dio) - len(nespojena)} spojeno s ustanovom iz tablice")
        # Bez praga: većina nespojenih su stvarno novi objekti na katastarskoj
        # čestici, pa nizak udio nije kvar. Ali svaki nespojeni naziv mora biti
        # vidljiv u logu, jer je jedini način da se uoči promašaj kao Mažuranić.
        for naziv in sorted(set(nespojena)):
            print(f"  nije spojeno s ustanovom iz tablice: {naziv}")
        svi.extend(dio)
    (IZLAZ / "ulaganja.json").write_text(
        json.dumps({"godine": sorted(ULAGANJA), "ulaganja": svi},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"zapisano → {(IZLAZ / 'ulaganja.json').relative_to(KORIJEN)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as greska:  # noqa: BLE001
        print(f"GREŠKA: {greska}", file=sys.stderr)
        sys.exit(1)
