"""BLACK-BOX TESTS - derived only from the specification (SRS), not from the code.

Techniques: Equivalence Class Partitioning (ECP) and Boundary Value Analysis (BVA).
Test-case IDs (BB-xx) match the black-box test tables in the report.
"""
import unittest

from ams.errors import ValidationError
from ams.services import compute_excess_fee
from ams import validators as v


class TestSeatSelection(unittest.TestCase):
    """parse_seat(seat, rows): valid seat = row 1..rows, column A-F.  Flight with rows = 20."""

    def test_BB01_valid_middle_seat(self):            # ECP valid class
        self.assertEqual(v.parse_seat("12C", 20), "12C")

    def test_BB02_lowercase_is_normalised(self):      # ECP valid class (case-insensitive)
        self.assertEqual(v.parse_seat(" 7d ", 20), "7D")

    def test_BB03_row_lower_boundary(self):           # BVA: row = 1 (min)
        self.assertEqual(v.parse_seat("1A", 20), "1A")

    def test_BB04_row_upper_boundary(self):           # BVA: row = rows (max)
        self.assertEqual(v.parse_seat("20F", 20), "20F")

    def test_BB05_row_below_minimum(self):            # BVA: row = 0
        with self.assertRaises(ValidationError):
            v.parse_seat("0A", 20)

    def test_BB06_row_above_maximum(self):            # BVA: row = rows + 1
        with self.assertRaises(ValidationError):
            v.parse_seat("21A", 20)

    def test_BB07_invalid_column(self):               # ECP invalid class: column G
        with self.assertRaises(ValidationError):
            v.parse_seat("5G", 20)

    def test_BB08_malformed_input(self):              # ECP invalid class: wrong format / empty
        for bad in ("A5", "", "12", "1 2C", None):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.parse_seat(bad, 20)


class TestBagWeight(unittest.TestCase):
    """validate_bag_weight: 0 < weight <= 32 kg."""

    def test_BB09_valid_weight(self):
        self.assertEqual(v.validate_bag_weight("18.5"), 18.5)

    def test_BB10_upper_boundary(self):               # BVA: 32.0 (max)
        self.assertEqual(v.validate_bag_weight("32"), 32.0)

    def test_BB11_just_above_upper_boundary(self):    # BVA: 32.1
        with self.assertRaises(ValidationError):
            v.validate_bag_weight("32.1")

    def test_BB12_just_above_lower_boundary(self):    # BVA: 0.1 (min valid)
        self.assertEqual(v.validate_bag_weight("0.1"), 0.1)

    def test_BB13_zero_and_negative(self):            # BVA / ECP invalid: <= 0
        for bad in ("0", "-5"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_bag_weight(bad)

    def test_BB14_non_numeric(self):                  # ECP invalid: not a number
        with self.assertRaises(ValidationError):
            v.validate_bag_weight("heavy")


class TestExcessBaggageFee(unittest.TestCase):
    """compute_excess_fee: free 15 kg, then Rs 500 per started kg."""

    def test_BB15_no_baggage(self):                   # BVA: 0 kg
        self.assertEqual(compute_excess_fee(0), 0)

    def test_BB16_exactly_allowance(self):            # BVA: 15.0 kg
        self.assertEqual(compute_excess_fee(15.0), 0)

    def test_BB17_just_over_allowance(self):          # BVA: 15.1 kg -> 1 started kg
        self.assertEqual(compute_excess_fee(15.1), 500)

    def test_BB18_whole_kg_over(self):                # ECP: 20.0 kg -> 5 kg
        self.assertEqual(compute_excess_fee(20.0), 2500)

    def test_BB19_negative_weight(self):              # ECP invalid
        with self.assertRaises(ValidationError):
            compute_excess_fee(-1)


class TestFlightFieldValidation(unittest.TestCase):
    def test_BB20_flight_number_classes(self):
        self.assertEqual(v.validate_flight_no("ai202"), "AI202")
        self.assertEqual(v.validate_flight_no("6E5021"), "6E5021")
        for bad in ("22202", "AI", "AI20202", "AI-202"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_flight_no(bad)

    def test_BB21_route_same_airport_rejected(self):
        self.assertEqual(v.validate_route("del", "bom"), ("DEL", "BOM"))
        with self.assertRaises(ValidationError):
            v.validate_route("DEL", "DEL")

    def test_BB22_seat_rows_boundaries(self):         # BVA on 1..40
        self.assertEqual(v.validate_rows("1"), 1)
        self.assertEqual(v.validate_rows("40"), 40)
        for bad in ("0", "41", "ten"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_rows(bad)

    def test_BB23_fare_boundaries(self):              # BVA on 500..200000
        self.assertEqual(v.validate_fare("500"), 500)
        self.assertEqual(v.validate_fare("200000"), 200000)
        for bad in ("499", "200001", "12.5"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_fare(bad)

    def test_BB24_gate_classes(self):
        self.assertIsNone(v.validate_gate(""))        # empty = unassigned
        self.assertEqual(v.validate_gate("b7"), "B7")
        self.assertEqual(v.validate_gate("D20"), "D20")
        for bad in ("E1", "A0", "A21", "7B"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_gate(bad)


class TestAccountValidation(unittest.TestCase):
    def test_BB25_password_rules(self):
        self.assertEqual(v.validate_password("abc123"), "abc123")     # BVA: length 6
        for bad in ("ab12", "abcdefg", "1234567"):                    # too short / no digit / no letter
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_password(bad)

    def test_BB26_phone_and_email(self):
        self.assertEqual(v.validate_phone("98765 43210"), "9876543210")
        self.assertEqual(v.validate_email("Om@Example.com"), "om@example.com")
        for bad in ("5876543210", "987654321"):
            with self.subTest(bad=bad), self.assertRaises(ValidationError):
                v.validate_phone(bad)
        with self.assertRaises(ValidationError):
            v.validate_email("om@example")


if __name__ == "__main__":
    unittest.main()
