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

    def test_2023_cita_plan2023_polje(self):
        geojson_2023 = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature",
                 "geometry": {"type": "Point", "coordinates": [15.9, 45.8]},
                 "properties": {"Vrsta_objekta": "PREDŠKOLSKE USTANOVE", "naziv": "DV Test",
                                "Adresa": "", "Opis_radova": "izrada projektne dokumentacije",
                                "Plan2023": 13000}},
            ],
        }
        u = gradi.parse_ulaganja(geojson_2023, 2023)
        self.assertEqual(u[0]["iznos"], 13000)

    def test_nepoznata_godina_puca_umjesto_null_iznosa(self):
        with self.assertRaises(Exception):
            gradi.parse_ulaganja(GEOJSON, 2025)


class TestPripojiCetvrt(unittest.TestCase):
    """Spajanje ulaganja s ustanovama iz tablice slobodnih mjesta."""

    def cetvrti(self):
        return {
            gradi.normaliziraj_naziv("DJEČJI VRTIĆ BAJKA"): "Trešnjevka - sjever",
            gradi.normaliziraj_naziv("DJEČJI VRTIĆ IVANE BRLIĆ MAŽURANIĆ"): "Donja Dubrava",
        }

    def test_spojeno_ulaganje_dobiva_cetvrt(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        gradi.pripoji_cetvrt(u, self.cetvrti(), {})
        bajka = next(x for x in u if x["naziv"].startswith('DV "Bajka"'))
        self.assertTrue(bajka["spojena"])
        self.assertEqual(bajka["cetvrt"], "Trešnjevka - sjever")

    def test_nespojeno_ulaganje_nema_cetvrt_i_vraca_se_u_popisu(self):
        u = gradi.parse_ulaganja(GEOJSON, 2024)
        nespojena = gradi.pripoji_cetvrt(u, self.cetvrti(), {})
        ivanja = next(x for x in u if x["naziv"] == "DV Ivanja Reka")
        self.assertFalse(ivanja["spojena"])
        self.assertIsNone(ivanja["cetvrt"])
        self.assertIn("DV Ivanja Reka", nespojena)

    def test_iznimka_spaja_ulaganje_kao_i_kontakt(self):
        # Isti naziv se ne smije normalizirati na dva mjesta po dva pravila —
        # 'DV I. B. Mažuranić' je postojeći vrtić u Cerskoj 22, Donja Dubrava.
        geojson = {
            "features": [
                {"geometry": {"coordinates": [16.042, 45.823]},
                 "properties": {"Vrsta_objekta": "PREDŠKOLSKE USTANOVE",
                                "naziv": "DV I. B. Mažuranić", "Adresa": "Cerska ulica 22",
                                "Opis_radova": "građenje", "plan24": "1500000"}},
            ],
        }
        u = gradi.parse_ulaganja(geojson, 2024)
        iznimke = {
            gradi.normaliziraj_naziv("DV I. B. Mažuranić"):
                gradi.normaliziraj_naziv("DJEČJI VRTIĆ IVANE BRLIĆ MAŽURANIĆ")
        }
        nespojena = gradi.pripoji_cetvrt(u, self.cetvrti(), iznimke)
        self.assertEqual(nespojena, [])
        self.assertTrue(u[0]["spojena"])
        self.assertEqual(u[0]["cetvrt"], "Donja Dubrava")

    def test_mapa_iznimaka_sadrzi_mazuranica(self):
        # regresija: bez ovog retka Donja Dubrava prikazuje 2 umjesto 4 ulaganja
        iznimke = gradi.ucitaj_iznimke()
        self.assertEqual(
            iznimke.get(gradi.normaliziraj_naziv("DV I. B. Mažuranić")),
            gradi.normaliziraj_naziv("DJEČJI VRTIĆ IVANE BRLIĆ MAŽURANIĆ"),
        )
