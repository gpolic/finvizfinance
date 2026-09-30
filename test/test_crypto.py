"""Offline fixture tests for the crypto scraper (see test_quote for the pattern)."""

import pandas as pd
import pytest
from conftest import blocked_response, html_response, use_session

from finvizfinance.crypto import Crypto
from finvizfinance.exceptions import FinvizBlockedError, FinvizParseError


def test_crypto_performance_real():
    use_session(html_response("crypto_perf.html"))
    df = Crypto().performance()
    # Sorted by Perf Day descending; percents scaled to fractions.
    assert list(df["Name"]) == ["Bitcoin", "Ethereum"]
    assert list(df["Ticker"]) == ["BTCUSD", "ETHUSD"]
    assert df.iloc[0]["Perf Day"] == 0.025
    assert df.iloc[0]["Price"] == 100000
    assert pd.isna(df.iloc[0]["Perf Quart"])


def test_crypto_performance_bad_json_raises_parse_error():
    use_session(html_response("perf_bad_json.html"))
    with pytest.raises(FinvizParseError):
        Crypto().performance()


def test_crypto_performance_drift_raises_parse_error():
    use_session(html_response("groups_table_drift.html"))
    with pytest.raises(FinvizParseError):
        Crypto().performance()


def test_crypto_performance_wall_raises_blocked_error():
    use_session(blocked_response())
    with pytest.raises(FinvizBlockedError):
        Crypto().performance()


def test_crypto_chart_url_mock(mocker):
    mocker.patch(
        "finvizfinance.crypto.image_scrap_function",
        return_value="image_scrap_functionurl",
    )
    assert Crypto().chart(crypto="test") == "image_scrap_functionurl"
