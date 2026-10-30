"""Small, transparent arithmetic examples. No network access or external packages."""

from dataclasses import asdict, dataclass
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from typing import Optional, Sequence, Union

Number = Union[str, int, Decimal]
MAX_VALUE = Decimal("1000000000000000")


def _number(value: Number, name: str) -> Decimal:
    """Reject floats, non-finite values and resource-heavy decimal inputs."""
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError(f"{name}: use a decimal string, integer or Decimal, not float")
    if len(str(value)) > 100:
        raise ValueError(f"{name}: input is too long")
    try:
        result = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name}: invalid decimal") from exc
    if not result.is_finite() or result < 0 or result > MAX_VALUE:
        raise ValueError(f"{name}: must be finite and between 0 and {MAX_VALUE}")
    # Fixed bounds keep arithmetic predictable; they are not legal/business limits.
    if len(result.as_tuple().digits) > 24 or not -12 <= result.as_tuple().exponent <= 15:
        raise ValueError(f"{name}: at most 24 digits and 12 decimal places are supported")
    return result


def _rounded(value: Decimal, places: int) -> Decimal:
    if isinstance(places, bool) or not isinstance(places, int) or not 0 <= places <= 6:
        raise ValueError("currency_places: choose an integer from 0 to 6")
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class RateComparison:
    previous_percent: Decimal
    current_percent: Decimal
    percentage_point_change: Decimal
    relative_percent_change: Optional[Decimal]


def compare_rates(previous_percent: Number, current_percent: Number) -> RateComparison:
    """Compare rates expressed as percentages: 4 -> 5 means +1 pp and +25%."""
    previous = _number(previous_percent, "previous_percent")
    current = _number(current_percent, "current_percent")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_UP)):
        difference = current - previous
        relative = None if previous == 0 else difference / previous * 100
        return RateComparison(previous, current, difference, relative)


@dataclass(frozen=True)
class QuoteLine:
    amount: Number
    tax_mode: str  # "included" or "excluded"


@dataclass(frozen=True)
class NormalizedLine:
    entered_amount: Decimal
    tax_mode: str
    gross_before_rounding: Decimal
    gross_rounded: Decimal


@dataclass(frozen=True)
class QuoteComparison:
    tax_rate_percent: Decimal
    currency_places: int
    lines: tuple[NormalizedLine, ...]
    total_before_rounding: Decimal
    total_round_once: Decimal
    total_sum_rounded_lines: Decimal
    rounding_difference: Decimal


def normalize_quotes(
    lines: Sequence[QuoteLine], tax_rate_percent: Number, currency_places: int = 0
) -> QuoteComparison:
    """Normalize quotes to tax-inclusive payable amounts under an explicit rate.

    An included amount is kept as entered. An excluded amount is multiplied by
    (1 + rate/100). This does not determine whether a transaction is taxable.
    """
    rate = _number(tax_rate_percent, "tax_rate_percent")
    if not lines or len(lines) > 10000:
        raise ValueError("lines: provide between 1 and 10000 quote lines")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_UP)):
        _rounded(Decimal(0), currency_places)
        normalized = []
        for index, line in enumerate(lines):
            if not isinstance(line, QuoteLine):
                raise ValueError("each quote must be a QuoteLine")
            amount = _number(line.amount, f"lines[{index}].amount")
            if line.tax_mode not in ("included", "excluded"):
                raise ValueError("tax_mode: choose 'included' or 'excluded'")
            gross = amount if line.tax_mode == "included" else amount * (1 + rate / 100)
            normalized.append(NormalizedLine(amount, line.tax_mode, gross, _rounded(gross, currency_places)))
        raw_total = sum((line.gross_before_rounding for line in normalized), Decimal(0))
        once = _rounded(raw_total, currency_places)
        line_sum = sum((line.gross_rounded for line in normalized), Decimal(0))
        return QuoteComparison(rate, currency_places, tuple(normalized), raw_total, once, line_sum, line_sum - once)


@dataclass(frozen=True)
class RentPeriod:
    months: int
    monthly_rent: Number


@dataclass(frozen=True)
class AnnualRentComparison:
    months: int
    baseline_annual_rent: Decimal
    actual_annual_rent: Decimal
    weighted_monthly_rent: Decimal
    annual_difference: Decimal
    relative_percent_change: Optional[Decimal]


def compare_annual_rent(
    baseline_monthly_rent: Number, periods: Sequence[RentPeriod]
) -> AnnualRentComparison:
    """Compare 12 full months with a constant-rent baseline, not net income.

    Periods must cover exactly 12 non-overlapping full months. Vacancy may be
    modeled as a period with zero rent. Day-based proration is not supported.
    """
    baseline_monthly = _number(baseline_monthly_rent, "baseline_monthly_rent")
    if not periods or len(periods) > 12:
        raise ValueError("periods: provide between 1 and 12 periods")
    with localcontext(Context(prec=50, rounding=ROUND_HALF_UP)):
        months = 0
        total = Decimal(0)
        for index, period in enumerate(periods):
            if not isinstance(period, RentPeriod):
                raise ValueError("each period must be a RentPeriod")
            if isinstance(period.months, bool) or not isinstance(period.months, int) or not 1 <= period.months <= 12:
                raise ValueError("months: each period requires an integer from 1 to 12")
            rent = _number(period.monthly_rent, f"periods[{index}].monthly_rent")
            months += period.months
            total += period.months * rent
        if months != 12:
            raise ValueError("periods must cover exactly 12 full months")
        baseline = baseline_monthly * 12
        difference = total - baseline
        relative = None if baseline == 0 else difference / baseline * 100
        return AnnualRentComparison(months, baseline, total, total / 12, difference, relative)


def to_json_value(result):
    """Return JSON-compatible data; decimals stay strings rather than floats."""
    def convert(value):
        if isinstance(value, Decimal):
            return format(value, "f")
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [convert(item) for item in value]
        return value
    return convert(asdict(result))
