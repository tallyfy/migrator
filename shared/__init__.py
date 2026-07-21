"""
Shared components used by every vendor migrator.

Vendor entry points run as scripts (``python <vendor>/src/main.py``), which puts
only ``<vendor>/src`` on ``sys.path`` -- the repo root is absent, so ``import
shared`` fails. Vendor modules that need these components therefore prepend the
repo root to ``sys.path`` before importing (see ``_bootstrap_shared`` in the
vendor instance transformers).

Without that bootstrap the imports silently fall back to ``None`` and the
migration keeps running with the untyped path, which is exactly how kick-off
data was being discarded unnoticed.
"""
