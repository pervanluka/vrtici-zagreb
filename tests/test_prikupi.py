import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORIJEN / "scripts"))
import parsiranje  # noqa: E402
import prikupi  # noqa: E402

FIXTURE = (KORIJEN / "tests" / "fixtures" / "slobodna-mjesta-2026-09-01.html").read_text(
    encoding="utf-8"
)


class TestProvjeraZbrojeva(unittest.TestCase):
    def setUp(self):
        self.retci = parsiranje.parse_retke(FIXTURE)
        self.zbrojevi = parsiranje.parse_zbrojeve(FIXTURE)

    def test_ispravni_podaci_prolaze(self):
        izracunato = prikupi.provjeri_zbrojeve(self.retci, self.zbrojevi)
        self.assertEqual(izracunato["ukupno"], 1237)

    def test_izmijenjen_redak_pada(self):
        self.retci[0]["slobodnih"] += 1
        with self.assertRaises(ValueError):
            prikupi.provjeri_zbrojeve(self.retci, self.zbrojevi)

    def test_izgubljen_redak_pada(self):
        # simulira promjenu HTML-a u kojoj parser tiho preskoči dio tablice
        with self.assertRaises(ValueError):
            prikupi.provjeri_zbrojeve(self.retci[:500], self.zbrojevi)

    def test_poruka_navodi_koji_zbroj_ne_valja(self):
        self.retci[0]["slobodnih"] += 1
        with self.assertRaises(ValueError) as ctx:
            prikupi.provjeri_zbrojeve(self.retci, self.zbrojevi)
        self.assertIn("ukupno", str(ctx.exception))


class TestSnapshoti(unittest.TestCase):
    def test_prazna_mapa_nema_zadnji(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(prikupi.zadnji_snapshot(Path(d)))

    def test_zadnji_je_najnoviji(self):
        with tempfile.TemporaryDirectory() as d:
            mapa = Path(d)
            for ime in ("2023-03-01.csv", "2026-09-01.csv", "2025-01-01.csv", "serija.csv"):
                (mapa / ime).write_text("", encoding="utf-8")
            self.assertEqual(prikupi.zadnji_snapshot(mapa), date(2026, 9, 1))

    def test_zapis_ima_datum_u_svakom_retku(self):
        with tempfile.TemporaryDirectory() as d:
            retci = parsiranje.parse_retke(FIXTURE)
            put = prikupi.zapisi_snapshot(Path(d), date(2026, 9, 1), retci)
            linije = put.read_text(encoding="utf-8").splitlines()
            self.assertEqual(linije[0], ",".join(prikupi.ZAGLAVLJE))
            self.assertEqual(len(linije), 1031)
            self.assertTrue(linije[1].startswith("2026-09-01,"))

    def test_serija_spaja_sve_snapshotove(self):
        with tempfile.TemporaryDirectory() as d:
            mapa = Path(d)
            retci = parsiranje.parse_retke(FIXTURE)[:3]
            prikupi.zapisi_snapshot(mapa, date(2025, 1, 1), retci)
            prikupi.zapisi_snapshot(mapa, date(2026, 9, 1), retci)
            serija = prikupi.obnovi_seriju(mapa)
            linije = serija.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(linije), 7)  # zaglavlje + 2 × 3 retka
            self.assertTrue(linije[1].startswith("2025-01-01,"))

    def test_ponovna_obnova_ne_udvostrucuje(self):
        # gradi.py obnavlja seriju pri svakoj izgradnji, pa se obnovi_seriju()
        # pokreće nad mapom u kojoj serija.csv već postoji — ako bi se čitala
        # kao snimka, retci bi se udvostručili pri svakom pokretanju.
        with tempfile.TemporaryDirectory() as d:
            mapa = Path(d)
            retci = parsiranje.parse_retke(FIXTURE)[:3]
            prikupi.zapisi_snapshot(mapa, date(2025, 1, 1), retci)
            prikupi.zapisi_snapshot(mapa, date(2026, 9, 1), retci)
            prikupi.obnovi_seriju(mapa)
            serija = prikupi.obnovi_seriju(mapa)
            self.assertEqual(len(serija.read_text(encoding="utf-8").splitlines()), 7)


if __name__ == "__main__":
    unittest.main()
