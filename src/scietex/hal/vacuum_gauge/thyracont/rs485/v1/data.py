"""
Thyracont RS485 Version 1 Data Module.

This module provides utility functions for encoding and decoding pressure and calibration data
for Thyracont's RS485 protocol, used in vacuum gauge communication (e.g., VSP model). Pressure
values (in millibars) are encoded into a 6-digit string format combining a 4-digit mantissa and a
2-digit exponent, while calibration values are encoded as scaled integers. The module uses the
`Decimal` class for precise floating-point manipulation.

Functions:
    f_exp(number: float) -> int
        Calculates the exponent of a number based on its decimal representation.
    f_man(number: float) -> Decimal
        Extracts the mantissa of a number as a normalized Decimal.
    _pressure_encode(pressure: float) -> str
        Encodes a pressure value into a 6-digit string (4-digit mantissa, 2-digit exponent).
    _pressure_decode(data: str) -> Optional[float]
        Decodes a pressure value from a 6-digit string.
    _calibration_encode(cal: float) -> str
        Encodes a calibration value into a string as a scaled integer.
    _calibration_decode(data: str) -> Optional[float]
        Decodes a calibration value from a string.
"""

from typing import Optional
from decimal import Decimal


def f_exp(number: float) -> int:
    """
    Get exponent of a number.

    Calculates the exponent of a number by analyzing its `Decimal` representation. The exponent is
    determined as the length of the digits plus the Decimal’s exponent minus 1, effectively giving
    the power of 10 needed to express the number in scientific notation.

    Parameters
    ----------
    number : float
        The input number to analyze.

    Returns
    -------
    int
        The exponent of the number in scientific notation (e.g., 2 for 123.45, -3 for 0.00123).
    """
    (_, digits, exponent) = Decimal(number).as_tuple()
    if isinstance(exponent, int):
        return len(digits) + exponent - 1
    raise ValueError(f"Invalid argument {number} in f_exp function.")


def f_man(number: float) -> Decimal:
    """
    Get mantissa of a number.

    Extracts the mantissa of a number by scaling it to a value between 1 and 10 (or 0 if the number
    is zero) using its exponent, then normalizing it to remove trailing zeros. The result is a
    `Decimal` object representing the significand in scientific notation.

    Parameters
    ----------
    number : float
        The input number to analyze.

    Returns
    -------
    Decimal
        The mantissa of the number (e.g., 1.2345 for 123.45, 1.23 for 0.00123).
    """
    return Decimal(number).scaleb(-f_exp(number)).normalize()


def _pressure_encode(pressure: float) -> str:
    """
    Convert pressure (in mbar) to data string.

    Encodes a pressure value in millibars into a 6-digit string format: the first 4 digits represent
    the mantissa (scaled to an integer between 1000 and 9999), and the last 2 digits represent the
    exponent offset by +20. This format accommodates a wide range of vacuum pressures.

    Parameters
    ----------
    pressure : float
        The pressure value in millibars (mbar) to encode (e.g., 1.23e-3).

    Returns
    -------
    str
        A 6-digit string encoding the pressure (e.g., "123403" for 1.23e-3 mbar, where 1234 is the
        mantissa and 03 is the exponent -20 + 20).

    Notes
    -----
    - Mantissa is calculated as `int(f_man(pressure) * 1000)`, giving 3 digits of precision.
    - Exponent is shifted by +20 (i.e., `f_exp(pressure) + 20`) to ensure non-negative values within
      typical vacuum ranges.
    """
    base = int(round(f_man(pressure) * 1000))
    exp = int(round(f_exp(pressure) + 20))
    return f"{base:04d}{exp:02d}"


def _pressure_decode(data: str) -> Optional[float]:
    """
    Parse pressure (in mbar) from response data.

    Decodes a 6-digit string into a pressure value in millibars. The first 4 digits are interpreted
    as the mantissa (scaled by 1000), and the last 2 digits are the exponent offset by -23 (adjusted
    from the encoded +20 shift). Returns None if decoding fails.

    Parameters
    ----------
    data : str
        A 6-digit string encoding the pressure (e.g., "123403" for 1.23e-3 mbar).

    Returns
    -------
    Optional[float]
        The decoded pressure value in millibars (mbar), or None if parsing fails.

    Raises
    ------
    TypeError
        Caught internally if `data` is not a string or convertible to integers.
    ValueError
        Caught internally if `data` cannot be parsed into integers (e.g., non-numeric).
    """
    try:
        if len(data) != 6:
            return None
        base: int = int(data[:4])
        exp: int = int(data[4:]) - 23
        return float(base * 10**exp)
    except (TypeError, ValueError):
        return None


def _calibration_encode(cal: float) -> str:
    """
    Encode a calibration value into a string.

    Converts a calibration factor (a float) into a string by scaling it by 100 and rounding to the
    nearest integer. This format is used for calibration registers in the Thyracont protocol.

    Parameters
    ----------
    cal : float
        The calibration value to encode (e.g., 1.23).

    Returns
    -------
    str
        The encoded calibration value as a string (e.g., "123" for 1.23).
    """
    return f"{int(round(cal * 100))}"


def _calibration_decode(data: str) -> Optional[float]:
    """
    Decode a calibration value from a string.

    Parses a string into a calibration factor by converting it to an integer and scaling it down
    by 100. Returns None if decoding fails.

    Parameters
    ----------
    data : str
        The string encoding the calibration value (e.g., "123" for 1.23).

    Returns
    -------
    Optional[float]
        The decoded calibration value, or None if parsing fails.

    Raises
    ------
    TypeError
        Caught internally if `data` is not a string or convertible to an integer.
    ValueError
        Caught internally if `data` cannot be parsed into an integer (e.g., non-numeric).
    """
    try:
        cal: float = int(data) / 100
        return cal
    except (TypeError, ValueError):
        return None
