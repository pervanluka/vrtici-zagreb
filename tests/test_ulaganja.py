# tests/test_ulaganja.py
import sys
import unittest
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORIJEN / "scripts"))
import gradi  # noqa: E402

GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [15.9452, 45.8017]},
         "properties": {"Vrsta_objekta": "PREDŠKOLSKE USTANOVE", "naziv": 'DV "Bajka", Humska 1',
                        "Adresa": "Humska 1", "Opis_radova": "energetska obnova", "plan24": "500000"}},
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [16.0, 45.83]},
         "properties": {"Vrsta_objekta": "PREDŠKOLSKE USTANOVE", "naziv": 'DV "Medo Brundo", PO Novi Retkovec',
                        "Adresa": "", "Opis_radova": "građenje", "plan24": "100000"}},
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [16.1, 45.79]},
         "properties": {"Vrsta_objekta": "PREDŠKOLSKE USTANOVE", "naziv": "DV Ivanja Reka",
                        "Adresa": "", "Opis_radova": "građenje i opremanje", "plan24": "100000"}},
        {"type": "Feature",
         "geometry": {"type": "Point", "coordinates": [15.98, 45.81]},
         "properties": {"Vrsta_objekta": "OSNOVNE ŠKOLE", "naziv": "OŠ Nekakva",
                        "Adresa": "", "Opis_radova": "obnova", "plan24": "900000"}},
    ],
}


class TestParseUlaganja(unittest.TestCase):
    def test_uzima_samo_predskolske(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        self.assertEqual(len(u), 3)
        self.assertNotIn("OŠ Nekakva", [x["naziv"] for x in u])

    def test_adresa_u_nazivu_se_skida(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        bajka = next(x for x in u if x["naziv"].startswith('DV "Bajka"'))
        self.assertEqual(bajka["kljuc"], gradi.normaliziraj_naziv("DJEČJI VRTIĆ BAJKA"))

    def test_zarez_prije_po_se_skida(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        medo = next(x for x in u if "MEDO" in x["kljuc"])
        self.assertEqual(medo["kljuc"], gradi.normaliziraj_naziv("DJEČJI VRTIĆ MEDO BRUNDO"))

    def test_iznos_je_broj(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        self.assertEqual(u[0]["iznos"], 500000)

    def test_koordinate_iz_geometrije(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        self.assertAlmostEqual(u[0]["x"], 15.9452)
        self.assertAlmostEqual(u[0]["y"], 45.8017)

    def test_godina_se_biljezi(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        self.assertTrue(all(x["godina"] == 2024 for x in u))
