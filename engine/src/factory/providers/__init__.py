"""Swappable backends. Each kind has a small interface in its package `__init__` and one module per backend,
so a new model or service is one new file plus one line in the registry; stages never import a backend directly."""
