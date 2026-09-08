import sys
import unittest
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORIJEN / "scripts"))
import gradi  # noqa: E402


class TestNormalizacija(unittest.TestCase):
    def test_gradski_vrtic(self):
        self.assertEqual(
            gradi.normaliziraj_naziv("DJEČJI VRTIĆ BAJKA"),
            gradi.normaliziraj_naziv("DV Bajka-matični objekt"),
        )

    def test_podrucni_objekt_pada_na_isti_kljuc(self):
        self.assertEqual(
            gradi.normaliziraj_naziv("DV Bajka-PO Humska"),
            gradi.normaliziraj_naziv("DJEČJI VRTIĆ BAJKA"),
        )

    def test_dadilja(self):
        self.assertEqual(
            gradi.normaliziraj_naziv("DAD BAJKA"), gradi.normaliziraj_naziv("DAD Bajka")
        )

    def test_navodnici_i_interpunkcija_se_zanemaruju(self):
        self.assertEqual(
            gradi.normaliziraj_naziv("DV OŠ MONTESSORI 'BARUNICE'"),
            gradi.normaliziraj_naziv("DV OŠ Montessori   BARUNICE"),
        )

    def test_razliciti_vrtici_ostaju_razliciti(self):
        self.assertNotEqual(
            gradi.normaliziraj_naziv("DV Montessori"),
            gradi.normaliziraj_naziv("DV OŠ Montessori BDV"),
        )


class TestCetvrt(unittest.TestCase):
    def test_velika_slova_i_crtica(self):
        self.assertEqual(
            gradi.kljuc_cetvrti("Trešnjevka - sjever"), gradi.kljuc_cetvrti("TREŠNJEVKA-SJEVER")
        )


KONTAKTI = [
    {
        "X": "15.9452", "Y": "45.8017", "Naziv": "DV Bajka-matični objekt",
        "Adresa": "Zorkovačka 8", "Telefon": "3699-015", "Email": "vrtic.bajka@zagreb.hr",
        "Web": "https://vrtic-bajka.zagreb.hr", "TipVrtica": "Matični",
        "VrstaVrtica": "Gradski DV", "GradskaCetvrt": "Trešnjevka-Sjever",
    },
    {
        "X": "15.938", "Y": "45.8089", "Naziv": "DV Bajka-PO Humska",
        "Adresa": "Humska 1", "Telefon": "3699-015", "Email": "vrtic.bajka@zagreb.hr",
        "Web": "https://vrtic-bajka.zagreb.hr", "TipVrtica": "Područni",
        "VrstaVrtica": "Gradski DV", "GradskaCetvrt": "Trešnjevka-Sjever",
    },
]

RETCI = [
    {
        "datum_stanja": "2026-09-01", "naziv": "DJEČJI VRTIĆ BAJKA", "vrsta": "Gradski DV",
        "cetvrt": "Trešnjevka - sjever", "dobna_skupina": "Jaslice",
        "uzrast": "2 do 3 godine", "program": "Redoviti", "slobodnih": 4,
    },
    {
        "datum_stanja": "2026-09-01", "naziv": "DJEČJI VRTIĆ NEPOSTOJEĆI", "vrsta": "Gradski DV",
        "cetvrt": "Trnje", "dobna_skupina": "Vrtić",
        "uzrast": "3 do 4 godine", "program": "Redoviti", "slobodnih": 7,
    },
]


class TestSpajanje(unittest.TestCase):
    def test_spojena_ustanova_ima_sve_svoje_objekte(self):
        ustanove, _ = gradi.spoji(RETCI, KONTAKTI, {})
        bajka = next(u for u in ustanove if u["naziv"] == "DJEČJI VRTIĆ BAJKA")
        self.assertEqual(len(bajka["objekti"]), 2)
        self.assertEqual(bajka["slobodnih_ukupno"], 4)
        self.assertAlmostEqual(bajka["objekti"][0]["x"], 15.9452)

    def test_nespojena_ustanova_ostaje_ali_bez_objekata(self):
        ustanove, nespojeni = gradi.spoji(RETCI, KONTAKTI, {})
        nepostojeci = next(u for u in ustanove if u["naziv"] == "DJEČJI VRTIĆ NEPOSTOJEĆI")
        self.assertEqual(nepostojeci["objekti"], [])
        self.assertEqual(nepostojeci["slobodnih_ukupno"], 7)
        self.assertIn("DJEČJI VRTIĆ NEPOSTOJEĆI", nespojeni)

    def test_iznimka_spaja_rucno(self):
        kontakti = KONTAKTI + [
            {
                "X": "16.0", "Y": "45.8", "Naziv": "DV OŠ Montessori BDV", "Adresa": "Matka Mandića 2",
                "Telefon": "", "Email": "", "Web": "", "TipVrtica": "Matični",
                "VrstaVrtica": "Privatni DV", "GradskaCetvrt": "Stenjevec",
            }
        ]
        retci = RETCI + [
            {
                "datum_stanja": "2026-09-01",
                "naziv": "DV OŠ MONTESSORI 'BARUNICE DEDEE VRANYCZANY'",
                "vrsta": "Privatni i vjerski DV", "cetvrt": "Stenjevec",
                "dobna_skupina": "Vrtić", "uzrast": "", "program": "", "slobodnih": 2,
            }
        ]
        iznimke = {
            gradi.normaliziraj_naziv("DV OŠ MONTESSORI 'BARUNICE DEDEE VRANYCZANY'"): gradi
            .normaliziraj_naziv("DV OŠ Montessori BDV")
        }
        ustanove, nespojeni = gradi.spoji(retci, kontakti, iznimke)
        montessori = next(u for u in ustanove if u["naziv"].startswith("DV OŠ MONTESSORI"))
        self.assertEqual(len(montessori["objekti"]), 1)
        self.assertNotIn(montessori["naziv"], nespojeni)

    def test_svaki_objekt_ima_koordinate(self):
        ustanove, _ = gradi.spoji(RETCI, KONTAKTI, {})
        for u in ustanove:
            for o in u["objekti"]:
                self.assertIsInstance(o["x"], float)
                self.assertIsInstance(o["y"], float)


if __name__ == "__main__":
    unittest.main()
