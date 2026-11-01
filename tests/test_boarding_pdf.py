"""Tests for the boarding-pass PDF export and its Code 128 barcode. Test-case IDs BP01-BP17."""
import re
import unittest
from datetime import datetime

from ams import boarding_pdf as bp_pdf
from ams.errors import AuthorizationError, BusinessRuleError, NotFoundError
from ams.models import BoardingPass
from tests.helpers import NOW, ServiceTestCase

PASS = BoardingPass("K7Q2MA", "Priya Verma", "AI202", "DEL", "BOM", datetime(2026, 11, 10, 17, 5),
                    datetime(2026, 11, 10, 16, 35), "A3", "4A", 2)

# Reference module strings (1 = bar, 0 = space) produced by the independent python-barcode library.
REFERENCE = {
    "ABC": "11010010000101000110001000101100010001000110110011011001100011101011",
    "K7Q2MA": "11010010000101100011101110110111011010001110110011100101011101100010100011000110001001001100011101011",
}


def modules(text):
    return "".join(("1" if i % 2 == 0 else "0") * w for i, w in enumerate(bp_pdf.code128_widths(text)))


class TestCode128(unittest.TestCase):
    def test_BP01_pattern_table_is_well_formed(self):
        patterns = bp_pdf._PATTERNS
        self.assertEqual(len(patterns), 106)                          # symbol values 0..105
        self.assertEqual(len(set(patterns)), 106)                     # all different
        for p in patterns:
            self.assertEqual((len(p), sum(map(int, p))), (6, 11))     # 3 bars + 3 spaces = 11 modules
        self.assertEqual(sum(map(int, bp_pdf._STOP)), 13)

    def test_BP02_symbol_values_and_checksum(self):
        self.assertEqual(bp_pdf.code128_symbols("ABC"), [104, 33, 34, 35, 1, 106])

    def test_BP03_matches_independent_reference_encoder(self):
        for text, expected in REFERENCE.items():
            self.assertEqual(modules(text), expected, text)

    def test_BP04_total_width_is_11_per_symbol_plus_stop(self):
        for text in ("K7Q2MA", "ABCDEF", "123456"):
            self.assertEqual(sum(bp_pdf.code128_widths(text)), 11 * (len(text) + 2) + 13)

    def test_BP05_rejects_characters_code128b_cannot_hold(self):
        for bad in ("café", "tab\there", "₹"):
            with self.assertRaises(ValueError):
                bp_pdf.code128_symbols(bad)


class TestPdfFile(unittest.TestCase):
    def setUp(self):
        self.pdf = bp_pdf.render_boarding_pass(PASS)

    def test_BP06_is_a_pdf_with_header_and_trailer(self):
        self.assertTrue(self.pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(self.pdf.rstrip().endswith(b"%%EOF"))

    def test_BP07_cross_reference_offsets_point_at_objects(self):
        start = int(re.search(rb"startxref\n(\d+)\n", self.pdf).group(1))
        self.assertTrue(self.pdf[start:].startswith(b"xref"))
        entries = re.findall(rb"(\d{10}) 00000 n ", self.pdf)
        self.assertEqual(len(entries), 7)
        for n, off in enumerate(entries, start=1):
            self.assertTrue(self.pdf[int(off):].startswith(f"{n} 0 obj".encode()), n)

    def test_BP08_stream_length_is_declared_correctly(self):
        length = int(re.search(rb"/Length (\d+)", self.pdf).group(1))
        body = self.pdf.split(b"stream\n", 1)[1].split(b"\nendstream", 1)[0]
        self.assertEqual(len(body), length)

    def test_BP09_contains_the_boarding_pass_details(self):
        for text in (b"BOARDING PASS", b"PRIYA VERMA", b"K7Q2MA", b"AI202", b"DEL", b"BOM", b"DELHI", b"MUMBAI",
                     b"17:05", b"16:35", b"(A3)", b"(4A)", b"(10 NOV 2026)", b"(002)"):
            self.assertIn(text, self.pdf, text)

    def test_BP10_unassigned_gate_prints_tba(self):
        data = bp_pdf.render_boarding_pass(BoardingPass("P9W1ZD", "Rahul Mehta", "6E5021", "BLR", "DEL",
                                                         datetime(2026, 11, 11, 15, 40), datetime(2026, 11, 11, 15, 10),
                                                         None, "12C", 17))
        self.assertIn(b"(TBA)", data)

    def test_BP11_special_characters_in_text_are_escaped(self):
        data = bp_pdf.render_boarding_pass(BoardingPass("K7Q2MA", "A (B) C\\D", "AI202", "DEL", "BOM", PASS.departure,
                                                         PASS.boarding_time, "A3", "4A", 2))
        self.assertIn(b"(A \\(B\\) C\\\\D)", data)      # ( ) and \ must be backslash-escaped inside a PDF string

    def test_BP12_file_name_and_unknown_airport_do_not_break_rendering(self):
        self.assertEqual(bp_pdf.suggested_filename(PASS), "BoardingPass_K7Q2MA_AI202.pdf")
        odd = BoardingPass("K7Q2MA", "Priya Verma", "AI202", "XXX", "YYY", PASS.departure, PASS.boarding_time,
                           "A3", "4A", 2)
        self.assertTrue(bp_pdf.render_boarding_pass(odd).startswith(b"%PDF"))

    def test_BP13_text_width_uses_helvetica_metrics(self):
        self.assertAlmostEqual(bp_pdf.text_width("A", 10), 6.67, places=2)
        self.assertGreater(bp_pdf.text_width("AAA", 10, bold=True), bp_pdf.text_width("AAA", 10))
        self.assertEqual((len(bp_pdf._W_REG), len(bp_pdf._W_BOLD)), (95, 95))


class TestBoardingPassExport(ServiceTestCase):
    def test_BP14_staff_can_export_a_checked_in_pass(self):
        name, data = self.checkin.boarding_pass_file(self.staff, "R4T9XB")       # seeded as checked in
        self.assertEqual(name, "BoardingPass_R4T9XB_AI202.pdf")
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertIn(b"RAHUL MEHTA", data)

    def test_BP15_passenger_can_export_only_their_own_pass(self):
        name, data = self.checkin.boarding_pass_file(self.rahul, "R4T9XB")
        self.assertIn(b"R4T9XB", data)
        with self.assertRaises(BusinessRuleError):
            self.checkin.boarding_pass_file(self.priya, "R4T9XB")                 # somebody else's pass

    def test_BP16_pass_exists_only_after_check_in(self):
        with self.assertRaises(BusinessRuleError):
            self.checkin.boarding_pass_file(self.staff, "K7Q2MA")                 # booked, not checked in
        self.checkin.check_in(self.staff, "K7Q2MA", now=NOW)
        name, data = self.checkin.boarding_pass_file(self.priya, "K7Q2MA")        # now available to the owner
        self.assertIn(b"PRIYA VERMA", data)
        self.assertIn(b"(002)", data)                                             # second passenger to board

    def test_BP17_unknown_pnr_and_logged_out_user(self):
        with self.assertRaises(NotFoundError):
            self.checkin.boarding_pass_file(self.staff, "ZZZZZZ")
        with self.assertRaises(AuthorizationError):
            self.checkin.boarding_pass_file(None, "R4T9XB")


if __name__ == "__main__":
    unittest.main()
