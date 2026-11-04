"""Verse host relay package.

Keep this initializer so setuptools.find_packages includes the relay modules
in installed wheels. The source checkout previously worked via Python's
namespace-package semantics, but the ISO wheel silently dropped all relay
modules without this marker, causing a real Live USB startup failure.

Relay classes remain imported from their individual modules to avoid
unnecessary import-time work during desktop startup.
"""
