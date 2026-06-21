import re

from ._helpers import runtime_path

BASE_URL = "https://www.digikey.com"
SEARCH_URL = f"{BASE_URL}/en/products/result?keywords={{query}}"
PRICE_PATTERN = re.compile(r"([$\u20a9\u20ac\u00a3]\s?[\d,]+(?:\.\d+)?)")
SEPARATOR = "=" * 80
DEFAULT_SHARE_PORT = 5000
SHARE_DIR = runtime_path("shared_specs")
NO_INFO = "정보 없음"

SPEC_MANUFACTURER = "제조사"
SPEC_MOUNTING_TYPE = "실장유형"
SPEC_INPUT_OFFSET_VOLTAGE = "전압 - 입력 오프셋"
SPEC_SUPPLY_CURRENT = "전류 - 공급"
SPEC_OUTPUT_CURRENT_PER_CHANNEL = "전류 - 출력/채널"
SPEC_SUPPLY_VOLTAGE_MIN = "전압 - 범위(최소)"
SPEC_SUPPLY_VOLTAGE_MAX = "전압 - 범위(최대)"
SPEC_OPERATING_TEMPERATURE = "작동 온도"
SPEC_GAIN_BANDWIDTH_PRODUCT = "이득 대역폭 곱"
SPEC_INPUT_BIAS_CURRENT = "전류 - 입력 바이어스"

MAIN_SPEC_ALIASES = {
    SPEC_MANUFACTURER: [
        "제조사",
        "manufacturer",
        "mfr",
    ],
    SPEC_MOUNTING_TYPE: [
        "실장유형",
        "실장 유형",
        "mounting type",
    ],
    SPEC_INPUT_OFFSET_VOLTAGE: [
        "전압 - 입력 오프셋",
        "voltage - input offset",
        "input offset voltage",
        "input offset",
    ],
    SPEC_SUPPLY_CURRENT: [
        "전류 - 공급",
        "전류 - 공급(최대)",
        "전류 - 공급 (최대)",
        "current - supply",
        "current - supply (max)",
        "supply current",
        "current supply",
        "current - quiescent",
    ],
    SPEC_OUTPUT_CURRENT_PER_CHANNEL: [
        "전류 - 출력/채널",
        "전류 - 출력 / 채널",
        "current - output / channel",
        "current - output/channel",
        "output current / channel",
        "output current per channel",
        "current - output",
    ],
    SPEC_SUPPLY_VOLTAGE_MIN: [
        "전압 - 범위(최소)",
        "전압 - 전원 범위(최소)",
        "전압 - 공급 범위(최소)",
        "전압 - 공급, 단일/이중(±)",
        "전압 - 전원, 단일/이중(±)",
        "voltage - supply span (min)",
        "voltage - supply span",
        "voltage - supply, single/dual (±) (min)",
        "voltage - supply, single/dual (±)",
        "voltage - supply, single/dual (+/-) (min)",
        "voltage - supply, single/dual (+/-)",
        "voltage - supply (min)",
        "voltage - supply",
        "supply voltage min",
        "voltage - input range (min)",
    ],
    SPEC_SUPPLY_VOLTAGE_MAX: [
        "전압 - 범위(최대)",
        "전압 - 전원 범위(최대)",
        "전압 - 공급 범위(최대)",
        "전압 - 공급, 단일/이중(±)",
        "전압 - 전원, 단일/이중(±)",
        "voltage - supply span (max)",
        "voltage - supply span",
        "voltage - supply, single/dual (±) (max)",
        "voltage - supply, single/dual (±)",
        "voltage - supply, single/dual (+/-) (max)",
        "voltage - supply, single/dual (+/-)",
        "voltage - supply (max)",
        "voltage - supply",
        "supply voltage max",
        "voltage - input range (max)",
    ],
    SPEC_OPERATING_TEMPERATURE: [
        "작동 온도",
        "동작 온도",
        "operating temperature",
        "temperature range",
    ],
}

CANDIDATE_SPEC_ALIASES = {
    SPEC_MANUFACTURER: MAIN_SPEC_ALIASES[SPEC_MANUFACTURER],
    SPEC_GAIN_BANDWIDTH_PRODUCT: [
        "이득 대역폭 곱",
        "gain bandwidth product",
        "gain bandwidth",
        "gbw",
        "bandwidth",
    ],
    SPEC_INPUT_BIAS_CURRENT: [
        "전류 - 입력 바이어스",
        "current - input bias",
        "input bias current",
        "bias current",
    ],
    SPEC_INPUT_OFFSET_VOLTAGE: MAIN_SPEC_ALIASES[SPEC_INPUT_OFFSET_VOLTAGE],
    SPEC_SUPPLY_CURRENT: MAIN_SPEC_ALIASES[SPEC_SUPPLY_CURRENT],
    SPEC_OUTPUT_CURRENT_PER_CHANNEL: MAIN_SPEC_ALIASES[SPEC_OUTPUT_CURRENT_PER_CHANNEL],
    SPEC_SUPPLY_VOLTAGE_MIN: MAIN_SPEC_ALIASES[SPEC_SUPPLY_VOLTAGE_MIN],
    SPEC_SUPPLY_VOLTAGE_MAX: MAIN_SPEC_ALIASES[SPEC_SUPPLY_VOLTAGE_MAX],
}

ATTRIBUTE_LABELS = [
    "Category",
    "Mfr",
    "Manufacturer",
    "Manufacturer Product Number",
    "Description",
    "Detailed Description",
    "Series",
    "Packaging",
    "Part Status",
    "Amplifier Type",
    "Number of Circuits",
    "Output Type",
    "Slew Rate",
    "Gain Bandwidth Product",
    "Current - Input Bias",
    "Voltage - Input Offset",
    "Current - Supply",
    "Current - Output / Channel",
    "Voltage - Supply Span (Min)",
    "Voltage - Supply Span (Max)",
    "Operating Temperature",
    "Mounting Type",
    "Package / Case",
    "Supplier Device Package",
    "Base Product Number",
    SPEC_MANUFACTURER,
    SPEC_MOUNTING_TYPE,
    "실장 유형",
    SPEC_INPUT_BIAS_CURRENT,
    SPEC_INPUT_OFFSET_VOLTAGE,
    SPEC_SUPPLY_CURRENT,
    SPEC_OUTPUT_CURRENT_PER_CHANNEL,
    SPEC_SUPPLY_VOLTAGE_MIN,
    SPEC_SUPPLY_VOLTAGE_MAX,
    SPEC_OPERATING_TEMPERATURE,
]
