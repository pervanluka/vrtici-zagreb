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

import parsiranje

KORIJEN = Path(__file__).resolve().parent.parent
SNAPSHOTI = KORIJEN / "data" / "slobodna-mjesta"
IZNIMKE = KORIJEN / "data" / "iznimke.csv"
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
                "postojeca": None,  # popunjava main() kad zna ključeve ustanova
            }
        )
    return ulaganja


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


def agregiraj_seriju(retci):
    """serija.csv → zbrojevi po datumu, ukupno / po četvrti / po vrsti.

    Datum koji nema nijedan redak za neku kategoriju ostaje odsutan, a ne nula:
    snapshot iz 2025. ne pokriva privatne vrtiće, i prikaz to mora razlikovati
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


def zapisi_provenijenciju(snapshotovi):
    """data/README.md — bez ovoga skup podataka nije provjerljiv, samo tvrdnja."""
    redovi = [
        "# Skup podataka: slobodna mjesta u zagrebačkim vrtićima",
        "",
        "Licenca: **CC-BY 4.0**. Izvor podataka: **Grad Zagreb**.",
        "",
        "Podaci o slobodnim mjestima prikupljeni su sa stranice",
        "<https://vrtici.zagreb.hr/slobodna-mjesta/187>, koja ih objavljuje mjesečno",
        "i pritom **prepisuje prethodni mjesec**. Ovaj repozitorij čuva svaki snimak,",
        "pa nastaje vremenska serija koja inače ne postoji.",
        "",
        "Kontakt podaci ustanova preuzimaju se s portala otvorenih podataka",
        "Grada Zagreba (<https://data.zagreb.hr>), pod Otvorenom dozvolom.",
        "",
        "## Shema",
        "",
        "`" + ",".join(ZAGLAVLJE) + "`",
        "",
        "## Snapshotovi",
        "",
        "| Datum stanja | Redaka | Slobodnih mjesta | Pokriveno |",
        "|---|---|---|---|",
    ]
    for s in snapshotovi:
        redovi.append(
            f"| {s['datum']} | {s['redaka']} | {s['mjesta']} | {', '.join(s['vrste'])} |"
        )
    redovi += [
        "",
        "## Ograničenja",
        "",
        "- Slobodna mjesta su na razini **matične ustanove**, ne pojedinog objekta.",
        "- Snapshot iz 2025. ne pokriva privatne i vjerske vrtiće; onaj iz 2023. ne pokriva obrte dadilja.",
        "- Gradska četvrt Brezovica ima ustanove, ali se ni u jednoj snimci slobodnih mjesta ne pojavljuje.",
        "- Ista četvrt je u izvorima pisana različito; u izvedenim prikazima svodi se na jedan naziv.",
        "- Podatak je mjesečni snimak, ne stanje uživo.",
        "",
        "Svaki snapshot proizveden je skriptom `scripts/prikupi.py` (odnosno",
        "`scripts/povijest.py` za 2023. i 2025.), a prije zapisa provjereno je da se",
        "zbroj redaka poklapa s kontrolnim brojkama koje izvor sam objavljuje.",
    ]
    (KORIJEN / "data" / "README.md").write_text("\n".join(redovi) + "\n", encoding="utf-8")


def sazetak_snapshota():
    sazeci = []
    for put in sorted(SNAPSHOTI.glob("*.csv")):
        if put.name == "serija.csv":
            continue
        with put.open(encoding="utf-8", newline="") as f:
            retci = list(csv.DictReader(f))
        sazeci.append(
            {
                "datum": put.stem,
                "redaka": len(retci),
                "mjesta": sum(int(r["slobodnih"]) for r in retci),
                "vrste": sorted({r["vrsta"] for r in retci}),
            }
        )
    return sazeci


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

    with SERIJA.open(encoding="utf-8", newline="") as f:
        serija = agregiraj_seriju(list(csv.DictReader(f)))
    (IZLAZ / "serija.json").write_text(
        json.dumps(serija, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    zapisi_provenijenciju(sazetak_snapshota())
    print(f"serija: {len(serija['datumi'])} snimaka; data/README.md osvježen")

    cetvrt_po_kljucu = {u["kljuc"]: u["cetvrt"] for u in ustanove}
    svi = []
    for godina, url in ULAGANJA.items():
        zahtjev = urllib.request.Request(url, headers={"User-Agent": "vrtici-zagreb/1.0"})
        with urllib.request.urlopen(zahtjev, timeout=60) as odgovor:
            dio = parse_ulaganja(json.load(odgovor), godina)
        for u in dio:
            u["postojeca"] = u["kljuc"] in cetvrt_po_kljucu
            # samo za postojeće ustanove znamo četvrt (dolazi iz spojene tablice
            # slobodnih mjesta) — za planirane objekte izvor nema taj podatak.
            u["cetvrt"] = cetvrt_po_kljucu.get(u["kljuc"])
        print(f"ulaganja {godina}: {len(dio)} predškolskih, "
              f"{sum(1 for u in dio if u['postojeca'])} spojeno s postojećom ustanovom")
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
