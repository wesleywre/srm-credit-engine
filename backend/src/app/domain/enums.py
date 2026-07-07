from enum import StrEnum


class BatchStatus(StrEnum):
    PENDING = "PENDING"
    SETTLED = "SETTLED"


class RateSource(StrEnum):
    MANUAL = "MANUAL"
    MOCK_PROVIDER = "MOCK_PROVIDER"
