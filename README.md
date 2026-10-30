# 생활 계산 검산 예제

금리의 `%`와 `%p`, 부가세 포함·별도 견적, 연중 월세 변경을 작은 함수로 직접 확인합니다. 계산 과정과 가정을 읽고 다른 숫자로 바꿔볼 수 있도록 만든 **교육용 Python 예제**입니다.

외부 패키지, 가입, API 키가 필요하지 않습니다. 코드에 네트워크 요청이나 입력값 저장 기능은 없습니다. 명령행에 입력한 값은 사용자의 셸 기록에 남을 수 있으므로 개인 정보나 실제 계약의 민감한 내용을 넣지 마세요.

## 빠른 시작

Python 3.10 이상을 권장합니다. 저장소 파일을 내려받은 폴더에서 실행하세요.

```sh
python cli.py rates 4 5
python cli.py quotes --tax-rate 10 --line included:110000 --line excluded:100000
python cli.py rent --baseline 1000000 --period 6:1000000 --period 6:1030000
python -m unittest discover -s tests -v
```

Windows에서 `python`이 연결되어 있지 않으면 설치 환경에 따라 `py`를 사용할 수 있습니다. 모든 금액은 같은 통화와 단위를 사용해야 합니다.

## 1. 4%에서 5%로: 1%p와 25%를 구분하기

```python
from calculations import compare_rates

result = compare_rates("4", "5")
print(result.percentage_point_change)  # 1
print(result.relative_percent_change)  # 25.00
```

- 퍼센트포인트 차이: `현재 비율 − 이전 비율`
- 상대 증가율(%): `(현재 비율 − 이전 비율) ÷ 이전 비율 × 100`

입력 `4`는 4%입니다. 이 함수에 `0.04`를 넣으면 **0.04%**로 해석됩니다.

5%에서 4%로 내리면 차이는 −1%p이고 상대 감소율은 −20%입니다. 올라갈 때와 내려갈 때 기준값이 달라 같은 증가율·감소율로 돌아오지 않을 수 있습니다. 이 차이는 [같은 비율로 올리고 내릴 때 기준금액이 바뀌는 계산](https://calc.ssslee.com/equal-percent-rise-fall-changing-base/)에서 더 살펴볼 수 있습니다.

이전 비율이 0이면 퍼센트포인트 차이는 계산하되 상대 증가율은 `None`으로 반환합니다. JSON 출력에서는 `null`입니다. 0에서 0으로 바뀐 경우도 상대 증가율을 임의로 0%라고 정하지 않습니다.

## 2. 포함·별도 견적을 같은 지급액 기준으로 맞추기

```python
from calculations import QuoteLine, normalize_quotes

result = normalize_quotes(
    [QuoteLine("110000", "included"), QuoteLine("100000", "excluded")],
    tax_rate_percent="10",
)
print(result.total_round_once)  # 220000
```

여기서 10%는 사용자가 **가정해 입력한 값**입니다. 코드는 세율, 과세·면세 여부, 공제 가능 여부나 세금계산서 작성 규칙을 판단하지 않습니다.

- `included`: 이미 세금이 포함된 지급액이므로 다시 세금을 더하지 않습니다.
- `excluded`: `입력 금액 × (1 + 입력 세율 ÷ 100)`으로 지급액을 계산합니다.

같은 세율을 적용할 수 있는 항목끼리만 한 번에 계산하세요. 실제 견적에서 각 항목의 세금 표시와 포함 범위를 먼저 확인해야 합니다. 관련 해설은 [부가세 포함·별도 금액이 섞인 견적 합산](https://calc.ssslee.com/mixed-vat-included-exclusive-quote-normalization/)에 있습니다.

### 반올림 위치도 결과에 표시합니다

기본 `currency_places=0`은 소수점 이하 없는 통화 단위로, `ROUND_HALF_UP` 방식으로 반올림합니다. 5.5는 6이 됩니다. 소수 둘째 자리까지 표시하려면 `currency_places=2` 또는 CLI의 `--places 2`를 사용합니다.

입력한 각 별도 금액이 5이고 가정 세율이 10%라면 두 항목은 각각 5.5입니다.

| 방식 | 결과 |
| --- | ---: |
| 합계 11.0을 한 번 반올림 | 11 |
| 각 5.5를 6으로 반올림한 뒤 합산 | 12 |

`total_round_once`와 `total_sum_rounded_lines`를 모두 반환하고, `rounding_difference`는 **항목별 반올림 합계 − 합계 한 번 반올림**입니다. 어느 방식을 실제 청구에 써야 하는지 결정하는 도구는 아닙니다.

## 3. 7월부터 월세가 3% 오르면 연간 임대료도 3% 늘까?

```python
from calculations import RentPeriod, compare_annual_rent

result = compare_annual_rent(
    "1000000",
    [RentPeriod(6, "1000000"), RentPeriod(6, "1030000")],
)
print(result.baseline_annual_rent)    # 12000000
print(result.actual_annual_rent)      # 12180000
print(result.relative_percent_change)  # 1.500
```

기준은 월 100만 원을 12개월 받는 경우입니다. 변경 후에는 6개월간 100만 원, 나머지 6개월간 103만 원을 받으므로 연간 차이는 18만 원, 증가율은 **1.5%**입니다.

`RentPeriod`의 기간은 서로 겹치지 않는 온전한 달이어야 하며 합계가 정확히 12개월이어야 합니다. 실제 월·시작일을 받는 프로그램이 아니므로 기간이 겹치지 않는지는 사용자가 확인해야 합니다. 하루 단위 일할 계산은 지원하지 않습니다.

공실을 모델링하려면 해당 기간의 월세를 0으로 입력할 수 있습니다. 이 값은 임대료 총액이지 관리비·세금·이자·수선비를 뺀 순이익이 아닙니다. 이 가상의 금액과 시점은 임대료 변경의 법적 허용 여부를 뜻하지 않습니다. 자세한 계산은 [연중 월세 변경과 연간 임대수입](https://calc.ssslee.com/midyear-rent-change-annual-income-weighting/)을 참고하세요.

## 숫자 입력과 한계

- 함수에는 문자열(`"0.1"`), 정수, `Decimal`을 사용합니다. 이진 부동소수점인 `float`는 실수로 오차를 들여오지 않도록 거부합니다.
- 음수 입력, NaN, Infinity, 잘못된 모드·월 수는 `ValueError`입니다. 감소 결과는 음수로 나올 수 있지만 이 예제의 원래 비율·금액 입력은 음수를 허용하지 않습니다.
- 월세 기준액이 0이면 상대 증가율은 `None`이며 금액 차이는 계산합니다.
- 개별 숫자는 0~10¹⁵, 최대 24자리 계수, 소수 12자리 이내로 제한합니다. 이는 프로그램 입력 보호 규칙이며 실제 거래 제한이 아닙니다.
- 견적은 최대 10,000개, 월세 기간은 최대 12개입니다.
- 내부 연산은 `Decimal` 정밀도 50자리와 `ROUND_HALF_UP`을 사용합니다. 나누어떨어지지 않는 비율·월평균은 50자리 정밀도에서 반올림된 값이며 무한 정밀도는 아닙니다.
- CLI JSON은 Decimal을 문자열로 출력합니다. 비율을 화면에서 더 짧게 표시할 때에도 비교와 검산 전 원래 결과를 보존하세요.

## 테스트

```sh
python -m unittest discover -s tests -v
```

테스트에는 정상 예제, 0인 기준값, 감소, 음수·비유한 입력 거부, 반올림 위치 차이, 12개월 합계 오류, 공실, CLI 정상 출력·오류 코드가 포함됩니다. 검산 결과 기록은 `TEST_RESULTS.md`를 참고하세요.

## 범위

이 저장소는 계산 과정을 공개한 학습 자료입니다. 세무·법률 판단, 금융기관의 대출 심사, 투자 의사결정을 대신하지 않습니다. 관련 해설 링크는 계산 가정을 더 읽기 위한 자료이며 프로그램 실행에 필요하지 않습니다.

English: Three dependency-free Python examples compare percentage points, normalize tax-inclusive/exclusive quotes, and calculate a weighted annual rent total. Decimal arithmetic, explicit assumptions and tests make the calculations inspectable. These are educational examples, not tax, legal or lending decisions.
