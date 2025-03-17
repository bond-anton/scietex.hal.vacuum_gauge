"""
Vacuum Gauge Package.

This package provides a modular framework for interfacing with vacuum gauges over serial
communication protocols, such as RS485, within the `scietex.hal` ecosystem. It supports both
client-side interaction with physical vacuum gauges and server-side emulation for testing and
development. The package is designed to be extensible, allowing for the addition of support for
different gauge manufacturers and models through subpackages.

Currently, the package includes support for Erstevak vacuum gauges via the `erstevak` subpackage,
which implements the Erstevak RS485 protocol (version 1). Future expansions may include additional
manufacturers or protocol versions.
"""

from .version import __version__
