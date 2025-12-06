from enum import Enum


class DeviceType(Enum):
    """
    Additional Wi-SUN Modules are included here for completeness but not all are supported.
    追加のWi-SUNモジュールは参考情報として含まれていますが、一部はサポート対象外です。
    Web archive of ROHM Wi-SUN B-Route modules as of November 29, 2025:
    ROHM Wi-SUN B-Routeモジュールのウェブアーカイブ(2025年11月29日時点):
    https://web.archive.org/web/20251129002611/https://www.chip1stop.com/sp/products/rohm_wi-sun-module
    """
    BP35A1 = 1  # Internal IC for RL7023 Stick-D/IPS. Now marked Obsolete and EOL
    BP35C0 = 2  # Wi-SUN/HAN Module. Not currently supported in Momonga
    BP35C1 = 3  # Wi-SUN/E-HAN Module. Not currently supported in Momonga
    BP35C2 = 4  # Internal IC for RS-WSUHA-P and RL7023 Stick-D/DSS