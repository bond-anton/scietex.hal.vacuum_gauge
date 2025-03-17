"""
Atmosphere Enum Module.

This module defines the `Atmosphere` enumeration, which represents the supported atmospheric gases
for vacuum gauge calculations. These gases are used to adjust pressure readings based on the
specific gas being measured. The enumeration supports initialization from string values for
compatibility with stored or serialized data.

Classes:
    - Atmosphere: An enumeration of supported atmospheric gases with string values and a method
      to convert from strings.

Methods:
    - from_string: Converts a string representation of a gas to the corresponding `Atmosphere`
        member.
"""

from enum import Enum


class Atmosphere(Enum):
    """
    Enumeration of supported atmospheric gases for vacuum gauge calculations.

    Members:
        AIR: Represents air, with value "Air".
        AR: Represents argon, with value "Ar".
        CO: Represents carbon monoxide, with value "CO".
        CO2: Represents carbon dioxide, with value "CO2".
        H2: Represents hydrogen, with value "H2".
        HE: Represents helium, with value "He".
        N2: Represents nitrogen, with value "N2".
        O2: Represents oxygen, with value "O2".
        NE: Represents neon, with value "Ne".
        KR: Represents krypton, with value "Kr".
        XE: Represents xenon, with value "Xe".

    Methods:
        from_string(cls, value: str) -> 'Atmosphere':
            Class method to convert a string to an `Atmosphere` member.
    """

    AIR = "Air"
    AR = "Ar"
    CO = "CO"
    CO2 = "CO2"
    H2 = "H2"
    HE = "He"
    N2 = "N2"
    O2 = "O2"
    NE = "Ne"
    KR = "Kr"
    XE = "Xe"

    @classmethod
    def from_string(cls, value: str) -> "Atmosphere":
        """
        Converts a string representation of a gas to the corresponding `Atmosphere` member.

        Args:
            value (str): The string representation of the gas (e.g., "Air", "H2", "Ne").

        Returns:
            Atmosphere: The corresponding `Atmosphere` member.

        Raises:
            ValueError: If the string does not match any supported gas value.
        """
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(
            f"Unknown atmosphere gas: {value}. Supported values are: {[m.value for m in cls]}"
        )
