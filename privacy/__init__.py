"""Local privacy inspection and sanitization utilities for Ouroboros."""

from .inspector import inspect_html_file
from .sanitizer import SanitizationResult, sanitize_elements

__all__ = ["inspect_html_file", "sanitize_elements", "SanitizationResult"]
