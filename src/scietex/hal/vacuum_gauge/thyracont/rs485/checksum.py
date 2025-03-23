"""
Checksum calculation functions.

Functions:
    _calc_checksum(msg: bytes) -> int: Calculates a custom checksum for a message.
    _check_checksum(msg: bytes, cs: int) -> bool: Verifies the checksum of a message.
"""


def calc_checksum(msg: bytes) -> int:
    """
    Calculate checksum for the message.

    Computes a custom checksum by summing the byte values of the message, taking the modulus 64,
    and adding 64 to ensure the result falls within the ASCII printable range (64-127).

    Parameters
    ----------
    msg : bytes
        The message for which to calculate the checksum, excluding the checksum byte itself.

    Returns
    -------
    int
        The calculated checksum value, an integer between 64 and 127.
    """
    return sum(list(msg)) % 64 + 64


def check_checksum(msg: bytes, cs: int) -> bool:
    """
    Check message checksum.

    Verifies if the provided checksum matches the calculated checksum for the message.

    Parameters
    ----------
    msg : bytes
        The message to verify, excluding the checksum byte.
    cs : int
        The checksum value to compare against, typically the last byte of the received frame.

    Returns
    -------
    bool
        True if the calculated checksum matches `cs`, False otherwise.
    """
    return calc_checksum(msg) == cs
