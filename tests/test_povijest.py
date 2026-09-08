import sys
import unittest
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORIJEN / "scripts"))
import povijest  # noqa: E402

WIDE = "\n".join(
    [
        "Gradska četvrt;Naziv dječjeg vrtića;Područni objekti;JASLICE;;;;;;;;;VRTIĆ;;;;;;;;;;",
        ";;;od 1 do 2 godine;;od 2 do 3 godine;;od 1 do 3 godine (mješovita);;UKUPNO;;;"
        "od 3 do 4 godine;;od 4 do 5 godine;;od 5 godina do OŠ;;od 3 godine do OŠ (mješovita);;UKUPNO;;",
        ";;;REDOVITI PROGRAM;POSEBNI PROGRAM;REDOVITI PROGRAM;POSEBNI PROGRAM;REDOVITI PROGRAM;"
        "POSEBNI PROGRAM;REDOVITI PROGRAM;POSEBNI PROGRAM;UKUPNO RED. + POS.;REDOVITI PROGRAM;"
        "POSEBNI PROGRAM;REDOVITI PROGRAM;POSEBNI PROGRAM;REDOVITI PROGRAM;POSEBNI PROGRAM;"
        "REDOVITI PROGRAM;POSEBNI PROGRAM;REDOVITI PROGRAM;POSEBNI PROGRAM;UKUPNO RED. + POS.",
        "DONJI GRAD;DV Budućnost;;0;0;0;0;0;0;0;0;0;0;0;4;0;0;0;0;0;4;0;4",
        ";DV Izvor;;0;0;1;0;0;0;1;0;1;0;0;0;0;0;0;0;0;0;0;0",
    ]
)

DADILJE = "\n".join(
    [
        'Gradska četvrt;GČ;"Naziv obrta";"Broj slobodnih mjesta od 1 godine do OŠ"',
        "DONJI GRAD;DONJI GRAD;DAD MALI TIM;0",
        ";DONJI GRAD;DAD MAMITA;3",
    ]
)

# Oblik stvarnog 2023. gradskog skupa: jednoredno zaglavlje (dobna+uzrast+program
# spojeni), četvrt s bilješkom o područnim objektima, naziv sa zvjezdicom,
# nedostajući razmak "OŠREDOVITI", i zbirni redak "UKUPNO" na dnu s NEpraznim
# nazivom (za razliku od 2025. formata).
GRADSKI_2023 = "\n".join(
    [
        "Gradska četvrt;NAZIV DJEČJEG VRTIĆA; JASLICE od 1 do 2 godine REDOVITI PROGRAM;"
        " JASLICE od 1 do 2 godine POSEBNI  PROGRAM;JASLICE UKUPNO REDOVITI PROGRAM;"
        "JASLICE UKUPNO POSEBNI PROGRAM;VRTIĆ od 5 godina do OŠREDOVITI PROGRAM;"
        "VRTIĆ od 4 do 5 godine REDOVITI PROGRAM;VRTIĆ UKUPNO REDOVITI PROGRAM",
        '"DONJI GRAD (*Gornji grad-Medveščak; Podsljeme)";Različak *;1;0;1;0;0;2;2',
        ";Vedri dani;0;0;0;0;3;0;3",
        ";UKUPNO;1;0;1;0;3;2;5",
        " PODACI O SLOBODNIM MJESTIMA — NASLOVNI REDAK;;;;;;;",
    ]
)

# Oblik stvarnog 2023. privatnog skupa: samo zbroj po dobnoj skupini (bez
# uzrasta/programa), zbirni redak "SVEUKUPNO" s praznim nazivom na dnu.
PRIVATNI_2023 = "\n".join(
    [
        "GRADSKA ČETVRT;NAZIV DJEČJEG VRTIĆA;UKUPAN BROJ SLOBODNIH MJESTA U JASLICAMA;"
        "UKUPAN BROJ SLOBODNIH MJESTA U VRTIĆIMA;UKUPAN BROJ SLOBODNIH MJESTA U JASLICAMA I VRTIĆIMA",
        "DONJI GRAD;MIRJAM WEILLER;0;10;10",
        "DONJI GRAD;SUNČEKO;0;0;0",
        "SVEUKUPNO;;0;10;10",
    ]
)


class TestUzrast(unittest.TestCase):
    def test_uklanja_prefiks_od(self):
        self.assertEqual(povijest.ocisti_uzrast("od 1 do 2 godine"), "1 do 2 godine")

    def test_zagrade_mjesovita(self):
        self.assertEqual(
            povijest.ocisti_uzrast("od 1 do 3 godine (mješovita)"), "1 do 3 godine mješovita"
        )

    def test_ispravak_godine_u_godina(self):
        # živi izvor piše "4 do 5 godina", skup iz 2025. piše "4 do 5 godine"
        self.assertEqual(povijest.ocisti_uzrast("od 4 do 5 godine"), "4 do 5 godina")

    def test_svi_uzrasti_odgovaraju_zivom_izvoru(self):
        retci = povijest.parse_gradski_wide(WIDE, "Gradski DV")
        zivi = {
            "1 do 2 godine", "2 do 3 godine", "1 do 3 godine mješovita",
            "3 do 4 godine", "4 do 5 godina", "5 godina do OŠ", "3 godine do OŠ mješovita",
        }
        self.assertTrue({r["uzrast"] for r in retci} <= zivi)


class TestWide(unittest.TestCase):
    def test_preskace_ukupno_stupce(self):
        retci = povijest.parse_gradski_wide(WIDE, "Gradski DV")
        self.assertNotIn("UKUPNO", {r["uzrast"] for r in retci})
        # 7 uzrasta × 2 programa × 2 vrtića
        self.assertEqual(len(retci), 28)

    def test_forward_fill_cetvrti(self):
        retci = povijest.parse_gradski_wide(WIDE, "Gradski DV")
        self.assertEqual({r["cetvrt"] for r in retci}, {"DONJI GRAD"})

    def test_dobna_skupina_iz_prvog_reda(self):
        retci = povijest.parse_gradski_wide(WIDE, "Gradski DV")
        jaslice = [r for r in retci if r["dobna_skupina"] == "Jaslice"]
        self.assertEqual(len(jaslice), 12)  # 3 uzrasta × 2 programa × 2 vrtića

    def test_zbroj_odgovara_ukupnom_stupcu(self):
        retci = povijest.parse_gradski_wide(WIDE, "Gradski DV")
        # iz fiksture: Budućnost ima 4, Izvor ima 1
        self.assertEqual(sum(r["slobodnih"] for r in retci), 5)


class TestDadilje(unittest.TestCase):
    def test_parsira_i_forward_filla(self):
        retci = povijest.parse_dadilje(DADILJE)
        self.assertEqual(len(retci), 2)
        self.assertEqual({r["vrsta"] for r in retci}, {"Obrt dadilja"})
        self.assertEqual({r["cetvrt"] for r in retci}, {"DONJI GRAD"})
        self.assertEqual(sum(r["slobodnih"] for r in retci), 3)

    def test_dadilje_nemaju_dobnu_skupinu_ni_program(self):
        retci = povijest.parse_dadilje(DADILJE)
        self.assertEqual({r["dobna_skupina"] for r in retci}, {""})
        self.assertEqual({r["program"] for r in retci}, {""})


class TestGradski2023(unittest.TestCase):
    def test_preskace_ukupno_stupce_i_redak(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        self.assertNotIn("UKUPNO", {r["uzrast"] for r in retci})
        self.assertNotIn("UKUPNO", {r["naziv"] for r in retci})
        # 4 stupca s mjestima (bez 3 UKUPNO stupca) × 2 vrtića
        self.assertEqual(len(retci), 8)

    def test_skida_biljesku_iz_cetvrti_i_forward_filla(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        self.assertEqual({r["cetvrt"] for r in retci}, {"DONJI GRAD"})

    def test_skida_zvjezdicu_iz_naziva(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        self.assertIn("Različak", {r["naziv"] for r in retci})

    def test_nedostajuci_razmak_prije_redoviti(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        self.assertIn("5 godina do OŠ", {r["uzrast"] for r in retci})

    def test_uzrast_4_do_5_ispravljen(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        self.assertIn("4 do 5 godina", {r["uzrast"] for r in retci})
        self.assertNotIn("4 do 5 godine", {r["uzrast"] for r in retci})

    def test_zbroj_odgovara_ukupnom_retku(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        # iz fiksture: Različak ima 1+0+2=3, Vedri dani ima 0+0+3=3 → 6
        self.assertEqual(sum(r["slobodnih"] for r in retci), 6)

    def test_svi_uzrasti_odgovaraju_zivom_izvoru(self):
        retci = povijest.parse_gradski_2023(GRADSKI_2023, "Gradski DV")
        zivi = {
            "1 do 2 godine", "2 do 3 godine", "1 do 3 godine mješovita",
            "3 do 4 godine", "4 do 5 godina", "5 godina do OŠ", "3 godine do OŠ mješovita",
        }
        self.assertTrue({r["uzrast"] for r in retci} <= zivi)


class TestPrivatni2023(unittest.TestCase):
    def test_parsira_zbroj_po_dobnoj_skupini(self):
        retci = povijest.parse_privatni_2023(PRIVATNI_2023)
        # 2 ustanove × 2 dobne skupine (Jaslice, Vrtić) — uključujući nule
        self.assertEqual(len(retci), 4)
        self.assertEqual({r["vrsta"] for r in retci}, {"Privatni i vjerski DV"})
        self.assertEqual({r["dobna_skupina"] for r in retci}, {"Jaslice", "Vrtić"})

    def test_nema_uzrast_ni_program(self):
        retci = povijest.parse_privatni_2023(PRIVATNI_2023)
        self.assertEqual({r["uzrast"] for r in retci}, {""})
        self.assertEqual({r["program"] for r in retci}, {""})

    def test_preskace_sveukupno_redak(self):
        retci = povijest.parse_privatni_2023(PRIVATNI_2023)
        nazivi = {r["naziv"] for r in retci}
        self.assertNotIn("SVEUKUPNO", nazivi)
        self.assertNotIn("", nazivi)
        self.assertEqual(sum(r["slobodnih"] for r in retci), 10)


if __name__ == "__main__":
    unittest.main()
