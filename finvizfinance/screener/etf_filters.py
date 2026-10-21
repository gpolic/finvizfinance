"""
.. module:: screener.etf_filters
   :synopsis: ETF screener filters, read live from finviz.

The ETF screener page (``/screener/etf``) embeds its filter definitions as
JSON. They are read from the live page on first use and cached for the
session, so options finviz adds, renames or removes are picked up without a
library release. If the page cannot be fetched or parsed, the bundled
snapshot in :mod:`finvizfinance.etf_constants` is used instead.
"""

from __future__ import annotations

import json
import logging
import re
import warnings
from typing import Any

import requests

from finvizfinance.constants import filter_dict
from finvizfinance.etf_constants import ETF_FILTERS
from finvizfinance.exceptions import FinvizError
from finvizfinance.util import validate_choice, web_scrap

logger = logging.getLogger(__name__)

ETF_SCREENER_URL = "https://finviz.com/screener/etf"

_FILTER_START = re.compile(r'\{"key":"etf_\w+","tab":"etf"')

# Stock filters are static; only ETF filters are read live.
STOCK_FILTERS: dict[str, dict] = {
    k: v for k, v in filter_dict.items() if k not in ETF_FILTERS
}

_cache: dict[str, dict] | None = None


def parse_etf_filters(html: str) -> dict[str, dict]:
    """Parse the ETF filter definitions embedded in the ETF screener page.

    Elite-only filters and options are left out: a free account cannot use
    them.

    Args:
        html(str): ETF screener page source
    Returns:
        filters(dict): filters in the ``filter_dict`` shape
    Raises:
        ValueError: no ETF filter definitions found in the page
    """
    decoder = json.JSONDecoder()
    filters: dict[str, dict] = {}
    for match in _FILTER_START.finditer(html):
        obj, _ = decoder.raw_decode(html, match.start())
        if obj.get("isEliteOnly"):
            continue
        filters[obj["title"]["short"]] = {
            "prefix": obj["key"],
            "option": {
                o["label"]: o["value"]
                for o in obj["options"]
                if not o.get("isEliteOnly")
            },
        }
    if not filters:
        raise ValueError("No ETF filters found in the page.")
    return filters


def get_etf_filters() -> dict[str, dict]:
    """Get the ETF filters, read live once per session.

    Falls back to the bundled snapshot (with a warning) when the live page
    cannot be fetched or parsed.

    Returns:
        filters(dict): filters in the ``filter_dict`` shape
    """
    global _cache
    if _cache is None:
        try:
            _cache = parse_etf_filters(str(web_scrap(ETF_SCREENER_URL)))
        except (FinvizError, requests.exceptions.RequestException, ValueError) as err:
            logger.debug("Reading live ETF filters failed", exc_info=True)
            warnings.warn(
                f"Could not read ETF filters from {ETF_SCREENER_URL} ({err}); "
                "using the bundled snapshot, which may be out of date.",
                stacklevel=2,
            )
            _cache = ETF_FILTERS
    return _cache


def refresh_etf_filters() -> None:
    """Drop the cached ETF filters so the next use reads them again."""
    global _cache
    _cache = None


def all_filters() -> dict[str, dict]:
    """Get stock and (live) ETF filters together.

    Returns:
        filters(dict): filters in the ``filter_dict`` shape
    """
    return {**STOCK_FILTERS, **get_etf_filters()}


def lookup_filter(name: str) -> dict[str, Any]:
    """Get one filter by name. Stock filters never trigger a request.

    Args:
        name(str): filter name, e.g. ``"Exchange"`` or ``"Sponsor"``
    Returns:
        filter(dict): the filter's ``prefix`` and ``option`` mapping
    """
    if name in STOCK_FILTERS:
        return STOCK_FILTERS[name]
    filters = all_filters()
    validate_choice(name, filters, "filter")
    return filters[name]
