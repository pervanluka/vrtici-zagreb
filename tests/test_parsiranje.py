import sys
import unittest
from datetime import date
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORIJEN / "scripts"))
import parsiranje  # noqa: E402

FIXTURE = (KORIJEN / "tests" / "fixtures" / "slobodna-mjesta-2026-09-01.html").read_text(
    encoding="utf-8"
)


class TestDatum(unittest.TestCase):
    def test_cita_datum_stanja(self):
        self.assertEqual(parsiranje.parse_datum(FIXTURE, date(2026, 9, 8)), date(2026, 9, 1))

    def test_prijelaz_godine(self):
        # u siječnju stranica još može pokazivati prosinačko stanje
        dokument = "<p>Na dan 1. prosinca slobodno je 10 upisnih mjesta.</p>"
        self.assertEqual(parsiranje.parse_datum(dokument, date(2027, 1, 5)), date(2026, 12, 1))

    def test_bez_datuma_puca(self):
        with self.assertRaises(ValueError):
            parsiranje.parse_datum("<p>ništa</p>", date(2026, 9, 8))


class TestRetci(unittest.TestCase):
    def test_broj_redaka(self):
        self.assertEqual(len(parsiranje.parse_retke(FIXTURE)), 1030)

    def test_prvi_redak(self):
        self.assertEqual(
            parsiranje.parse_retke(FIXTURE)[0],
            {
                "naziv": "DJEČJI VRTIĆ BAJKA",
                "vrsta": "Gradski DV",
                "cetvrt": "Trešnjevka - sjever",
                "dobna_skupina": "Jaslice",
                "uzrast": "1 do 2 godine",
                "program": "Redoviti",
                "slobodnih": 0,
            },
        )

    def test_poznate_vrste(self):
        vrste = {r["vrsta"] for r in parsiranje.parse_retke(FIXTURE)}
        self.assertEqual(vrste, {"Gradski DV", "Privatni i vjerski DV", "Obrt dadilja"})

    def test_bez_tablice_puca(self):
        with self.assertRaises(ValueError):
            parsiranje.parse_retke("<html><body>nema tablice</body></html>")


class TestZbrojevi(unittest.TestCase):
    def test_kontrolni_zbrojevi(self):
        self.assertEqual(
            parsiranje.parse_zbrojeve(FIXTURE),
            {
                "ukupno": 1237,
                "gradski": 803,
                "gradski_jaslice": 233,
                "gradski_vrtic": 570,
                "privatni": 363,
                "privatni_jaslice": 192,
                "privatni_vrtic": 171,
                "dadilje": 71,
            },
        )


if __name__ == "__main__":
    unittest.main()
