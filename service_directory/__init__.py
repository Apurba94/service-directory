"""Service Directory: find the right local service for a referral."""
from . import core
from .web import create_app

__all__ = ["core", "create_app"]
