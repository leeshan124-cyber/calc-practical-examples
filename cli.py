"""Command-line interface. Run `python cli.py --help`."""

import argparse
import json

from calculations import (
    QuoteLine, RentPeriod, compare_annual_rent, compare_rates,
    normalize_quotes, to_json_value,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Transparent percentage, quote and annual-rent arithmetic")
    subparsers = parser.add_subparsers(dest="command", required=True)
    rates = subparsers.add_parser("rates", help="Compare two rates, entered as percent numbers")
    rates.add_argument("previous")
    rates.add_argument("current")
    quotes = subparsers.add_parser("quotes", help="Normalize tax-inclusive and tax-exclusive quotes")
    quotes.add_argument("--tax-rate", required=True, help="An assumed percentage, e.g. 10; not a legal determination")
    quotes.add_argument("--places", type=int, default=0, help="Currency decimal places, 0 to 6; default 0")
    quotes.add_argument("--line", action="append", required=True, metavar="MODE:AMOUNT", help="Repeat: included:110000 or excluded:100000")
    rent = subparsers.add_parser("rent", help="Compare exactly 12 full months against a constant baseline")
    rent.add_argument("--baseline", required=True, help="Baseline monthly rent")
    rent.add_argument("--period", action="append", required=True, metavar="MONTHS:RENT", help="Repeat, e.g. 6:1000000 and 6:1030000")
    args = parser.parse_args(argv)
    try:
        if args.command == "rates":
            result = compare_rates(args.previous, args.current)
        elif args.command == "quotes":
            lines = []
            for item in args.line:
                mode, amount = item.split(":", 1)
                lines.append(QuoteLine(amount, mode))
            result = normalize_quotes(lines, args.tax_rate, args.places)
        else:
            periods = []
            for item in args.period:
                months, amount = item.split(":", 1)
                periods.append(RentPeriod(int(months), amount))
            result = compare_annual_rent(args.baseline, periods)
    except (ValueError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(to_json_value(result), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
