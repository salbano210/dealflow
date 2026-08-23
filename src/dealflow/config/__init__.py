"""Configuration loading & validation.

All user-editable configuration lives in YAML files under `config/` at the
repo root. This package loads those files, validates them with Pydantic,
and exposes typed objects to the rest of the application.

If any config file is invalid, `load_all()` raises before any pipeline
work is done -- we never run with half-broken config.
"""

from dealflow.config.loader import AppConfig, load_all

__all__ = ["AppConfig", "load_all"]
