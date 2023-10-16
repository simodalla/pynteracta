from enum import IntEnum, StrEnum


class FieldTypeEnum(IntEnum):
    INT = 1
    BIGINT = 2
    DECIMAL = 3
    DATE = 4
    DATETIME = 5
    STRING = 6
    ENUM = 7
    ENUM_LIST = 8
    TEXT_AREA = 9
    FLAG = 10
    DELTA_AREA = 11
    FEEDBACK = 12
    HIERARCHICAL_ENUM = 13
    LINK = 14
    GENERIC_ENTITY_LIST = 15


class FieldFilterTypeEnum(IntEnum):
    EQUAL = 1
    INTERVAL = 2
    LIKE = 3
    IN = 4
    CONTAINS = 5
    IS_NULL_OR_IN = 6
    IS_EMPTY = 7


class LoginProviderEnum(StrEnum):
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    CUSTOM = "custom"
