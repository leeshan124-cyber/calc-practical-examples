import contextlib
import io
import json
import unittest
from decimal import Decimal as D, localcontext

from calculations import (
    QuoteLine, RentPeriod, compare_annual_rent, compare_rates,
    normalize_quotes, to_json_value,
)
from cli import main


class RatesTests(unittest.TestCase):
    def test_increase(self):
        result = compare_rates("4", "5")
        self.assertEqual(result.percentage_point_change, D("1"))
        self.assertEqual(result.relative_percent_change, D("25"))

    def test_decrease(self):
        result = compare_rates("5", "4")
        self.assertEqual(result.percentage_point_change, D("-1"))
        self.assertEqual(result.relative_percent_change, D("-20"))

    def test_zero_baseline_does_not_invent_a_percentage(self):
        self.assertIsNone(compare_rates("0", "5").relative_percent_change)
        self.assertEqual(compare_rates("0", "5").percentage_point_change, D("5"))

    def test_zero_to_zero_also_undefined(self):
        self.assertIsNone(compare_rates(0, 0).relative_percent_change)

    def test_drop_to_zero(self):
        self.assertEqual(compare_rates(10, 0).relative_percent_change, D("-100"))

    def test_decimal_input(self):
        self.assertEqual(compare_rates(D("0.1"), "0.2").relative_percent_change, D("100"))

    def test_bad_inputs(self):
        for value in ("NaN", "sNaN", "Infinity", "-Infinity", "-1", "abc", 0.1, True, None, "1e16", "0e-999999999", "1e-13", "1" * 101):
            with self.subTest(value=value), self.assertRaises(ValueError):
                compare_rates(value, "5")

    def test_current_must_also_be_valid(self):
        with self.assertRaises(ValueError):
            compare_rates("5", "-2")

    def test_does_not_depend_on_callers_precision(self):
        with localcontext() as ctx:
            ctx.prec = 2
            self.assertEqual(compare_rates("3.25", "4.55").relative_percent_change, D("40"))


class QuoteTests(unittest.TestCase):
    def test_mixed_lines(self):
        result = normalize_quotes([QuoteLine("110000", "included"), QuoteLine("100000", "excluded")], "10")
        self.assertEqual(result.total_round_once, D("220000"))
        self.assertEqual(result.lines[0].gross_before_rounding, D("110000"))

    def test_rounding_order_difference(self):
        result = normalize_quotes([QuoteLine("1", "excluded")] * 3, "10")
        self.assertEqual(result.total_before_rounding, D("3.3"))
        self.assertEqual(result.total_round_once, D("3"))
        self.assertEqual(result.total_sum_rounded_lines, D("3"))
        # Half-up at a per-line half-unit produces a real difference.
        result = normalize_quotes([QuoteLine("5", "excluded")] * 2, "10")
        self.assertEqual(result.total_round_once, D("11"))
        self.assertEqual(result.total_sum_rounded_lines, D("12"))
        self.assertEqual(result.rounding_difference, D("1"))

    def test_zero_rate(self):
        self.assertEqual(normalize_quotes([QuoteLine("100", "excluded")], 0).total_round_once, D("100"))

    def test_zero_amount(self):
        self.assertEqual(normalize_quotes([QuoteLine(0, "included")], "10").total_round_once, D(0))

    def test_cent_rounding(self):
        result = normalize_quotes([QuoteLine("1.005", "included")], "10", 2)
        self.assertEqual(result.total_round_once, D("1.01"))

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            normalize_quotes([QuoteLine(1, "maybe")], "10")

    def test_invalid_rate(self):
        for rate in ("NaN", "-1", 0.1):
            with self.subTest(rate=rate), self.assertRaises(ValueError):
                normalize_quotes([QuoteLine(1, "included")], rate)

    def test_invalid_amount(self):
        with self.assertRaises(ValueError):
            normalize_quotes([QuoteLine("Infinity", "included")], "10")

    def test_invalid_precision(self):
        for places in (-1, 7, True, 0.5):
            with self.subTest(places=places), self.assertRaises(ValueError):
                normalize_quotes([QuoteLine(1, "included")], 10, places)

    def test_empty_and_oversized(self):
        for lines in ([], [QuoteLine(1, "included")] * 10001):
            with self.assertRaises(ValueError):
                normalize_quotes(lines, 10)

    def test_wrong_line_type(self):
        with self.assertRaises(ValueError):
            normalize_quotes([(1, "included")], 10)

    def test_input_bounds(self):
        result = normalize_quotes([QuoteLine("1000000000000000", "excluded")], "1000000000000000")
        self.assertEqual(result.total_round_once, D("10000000000001000000000000000"))


class RentTests(unittest.TestCase):
    def test_july_increase(self):
        result = compare_annual_rent("1000000", [RentPeriod(6, "1000000"), RentPeriod(6, "1030000")])
        self.assertEqual(result.baseline_annual_rent, D("12000000"))
        self.assertEqual(result.actual_annual_rent, D("12180000"))
        self.assertEqual(result.weighted_monthly_rent, D("1015000"))
        self.assertEqual(result.relative_percent_change, D("1.5"))

    def test_one_month_vacancy(self):
        result = compare_annual_rent("100", [RentPeriod(11, "100"), RentPeriod(1, 0)])
        self.assertEqual(result.actual_annual_rent, D("1100"))
        self.assertEqual(result.annual_difference, D("-100"))

    def test_unchanged(self):
        self.assertEqual(compare_annual_rent(100, [RentPeriod(12, 100)]).relative_percent_change, D(0))

    def test_zero_baseline(self):
        self.assertIsNone(compare_annual_rent(0, [RentPeriod(12, 100)]).relative_percent_change)

    def test_month_sum(self):
        for periods in ([RentPeriod(11, 10)], [RentPeriod(6, 10), RentPeriod(7, 10)]):
            with self.assertRaises(ValueError):
                compare_annual_rent(10, periods)

    def test_invalid_months(self):
        for months in (0, -1, 13, 12.0, True):
            with self.subTest(months=months), self.assertRaises(ValueError):
                compare_annual_rent(10, [RentPeriod(months, 10)])

    def test_invalid_rent(self):
        for amount in (-1, "NaN", "Infinity", 0.3):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                compare_annual_rent(10, [RentPeriod(12, amount)])

    def test_invalid_baseline(self):
        with self.assertRaises(ValueError):
            compare_annual_rent(-1, [RentPeriod(12, 10)])

    def test_empty_and_wrong_period_type(self):
        for periods in ([], [(12, 10)]):
            with self.assertRaises(ValueError):
                compare_annual_rent(10, periods)

    def test_twelve_periods(self):
        self.assertEqual(compare_annual_rent(1, [RentPeriod(1, 1)] * 12).actual_annual_rent, D(12))


class InterfaceTests(unittest.TestCase):
    def invoke(self, argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(argv), 0)
        return json.loads(output.getvalue())

    def test_rate_cli(self):
        self.assertEqual(self.invoke(["rates", "4", "5"])["relative_percent_change"], "25.00")

    def test_quote_cli(self):
        result = self.invoke(["quotes", "--tax-rate", "10", "--line", "included:110000", "--line", "excluded:100000"])
        self.assertEqual(result["total_round_once"], "220000")

    def test_rent_cli(self):
        result = self.invoke(["rent", "--baseline", "1000000", "--period", "6:1000000", "--period", "6:1030000"])
        self.assertEqual(D(result["relative_percent_change"]), D("1.5"))

    def test_cli_error(self):
        for argv in (["quotes", "--tax-rate", "10", "--line", "oops"], ["rent", "--baseline", "1", "--period", "oops:2"], ["rates", "NaN", "1"]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main(argv)
            self.assertEqual(error.exception.code, 2)

    def test_json_undefined_percentage(self):
        self.assertIsNone(to_json_value(compare_rates(0, 1))["relative_percent_change"])


if __name__ == "__main__":
    unittest.main()
