"""Offline fixture tests for the quote scrapers.

This module is the exemplar the other scraper test modules copy: each scraper
is exercised through the injected-session seam against saved HTML, covering the
four canonical cases — real 200, Drifted fixture, Cloudflare Wall, and a
missing optional field.
"""

import pytest
from conftest import (
    FakeResponse,
    blocked_response,
    html_response,
    load_fixture,
    use_session,
)

from finvizfinance.exceptions import FinvizBlockedError, FinvizParseError
from finvizfinance.quote import Statements, finvizfinance


def _stock(fixture):
    """Build a finvizfinance bound to a saved quote fixture."""
    use_session(html_response(fixture))
    return finvizfinance("AAPL")


# --- ticker_fundament: the four canonical cases -----------------------------


def test_fundament_real():
    fundament = _stock("quote_aapl.html").ticker_fundament()
    assert fundament["Company"] == "Apple Inc."
    assert fundament["Sector"] == "Technology"
    assert fundament["Industry"] == "Consumer Electronics"
    assert fundament["Country"] == "USA"
    assert fundament["Exchange"] == "NASDAQ"
    assert fundament["P/E"] == "25.50"
    assert fundament["Market Cap"] == "3050.00B"
    assert fundament["52W Range From"] == "164.08"
    assert fundament["52W Range To"] == "260.10"
    assert fundament["Volatility W"] == "1.50%"
    assert fundament["Volatility M"] == "2.00%"
    assert fundament["Optionable"] == "Yes"
    assert fundament["EPS next Y"] == "7.50"
    assert fundament["EPS next Y Percentage"] == "8.20%"


def test_fundament_drift_raises_parse_error():
    stock = _stock("quote_drift.html")
    with pytest.raises(FinvizParseError) as exc:
        stock.ticker_fundament()
    assert exc.value.selector == "table.snapshot-table2"


def test_fundament_wall_raises_blocked_error():
    use_session(blocked_response())
    with pytest.raises(FinvizBlockedError):
        finvizfinance("AAPL")


def test_fundament_missing_optional_classification_warns():
    stock = _stock("quote_etf.html")
    with pytest.warns(UserWarning):
        fundament = stock.ticker_fundament()
    assert fundament["Company"] == "SPDR S&P 500 ETF Trust"
    assert fundament["Sector"] is None
    assert fundament["Industry"] is None
    assert fundament["Country"] is None
    assert fundament["Exchange"] is None


def test_fundament_renamed_links_recovered_via_fallback():
    # Drift: the quote-links div was renamed; the guard falls back to the
    # stable screener-filter anchors and still resolves the classification.
    fundament = _stock("quote_renamed_links.html").ticker_fundament()
    assert fundament["Sector"] == "Technology"
    assert fundament["Industry"] == "Consumer Electronics"
    assert fundament["Country"] == "USA"
    assert fundament["Exchange"] == "NASDAQ"


def test_fundament_spans_multiple_snapshot_tables():
    # Regression for issue #156: finviz now splits the fundamentals across
    # several ``snapshot-table2`` tables inside a wrapper div. The parser must
    # read every table, not just the first, so fields in later tables are kept.
    fundament = _stock("quote_multi_table.html").ticker_fundament()
    # classification still resolves (via the screener-filter href fallback)
    assert fundament["Company"] == "International Business Machines Corp"
    assert fundament["Sector"] == "Technology"
    assert fundament["Exchange"] == "NYSE"
    # first table
    assert fundament["P/E"] == "20.40"
    assert fundament["Market Cap"] == "216.57B"
    # second table (missed entirely before the fix)
    assert fundament["ROE"] == "34.55%"
    assert fundament["Shs Outstand"] == "942.00M"
    assert fundament["Volatility W"] == "2.10%"
    assert fundament["Volatility M"] == "2.62%"
    # third table (also missed before the fix), incl. the EPS-next-Y dup split
    assert fundament["Perf YTD"] == "-22.40%"
    assert fundament["Target Price"] == "245.29"
    assert fundament["Price"] == "229.87"
    assert fundament["EPS next Y"] == "13.15"
    assert fundament["EPS next Y Percentage"] == "6.79%"


def test_fundament_series_output_format():
    df = _stock("quote_aapl.html").ticker_fundament(output_format="series")
    assert df.loc["Company", "Stat"] == "Apple Inc."


# --- other quote methods (ticket 06) ----------------------------------------


def test_ticker_description():
    desc = _stock("quote_aapl.html").ticker_description()
    assert "designs, manufactures" in desc


def test_ticker_peer():
    assert _stock("quote_aapl.html").ticker_peer() == ["MSFT", "GOOGL", "AMZN"]


def test_ticker_etf_holders():
    assert _stock("quote_aapl.html").ticker_etf_holders() == ["SPY", "QQQ", "VOO"]


def test_ticker_peer_absent_returns_empty_and_warns():
    stock = _stock("quote_etf.html")
    with pytest.warns(UserWarning):
        assert stock.ticker_peer() == []


def test_ticker_outer_ratings():
    df = _stock("quote_aapl.html").ticker_outer_ratings()
    assert list(df["Status"]) == ["Upgrade"]
    assert list(df["Outer"]) == ["Morgan Stanley"]


def test_ticker_outer_ratings_absent_returns_none_and_warns():
    stock = _stock("quote_etf.html")
    with pytest.warns(UserWarning):
        assert stock.ticker_outer_ratings() is None


def test_ticker_news():
    df = _stock("quote_aapl.html").ticker_news()
    assert list(df["Title"]) == ["Apple beats earnings", "Analyst raises target"]
    assert list(df["Source"]) == ["Reuters", "CNBC"]


def test_ticker_news_strips_title_whitespace():
    html = load_fixture("quote_aapl.html").replace(
        ">Apple beats earnings<", ">\r\n        Apple beats earnings\r\n    <"
    )
    use_session(FakeResponse(text=html))
    df = finvizfinance("AAPL").ticker_news()
    assert df["Title"].iloc[0] == "Apple beats earnings"


# The current snapshot layout: two-value cells and a merged Option/Short cell.
CURRENT_SNAPSHOT_ROWS = (
    "<tr><td>Option/Short</td><td>Yes / No</td><td>Trades</td><td>\n\n</td></tr>"
    "<tr><td>EPS past 3/5Y</td><td>6.89% 17.91%</td>"
    "<td>Dividend TTM</td><td>1.06 (0.31%)</td></tr>"
    "<tr><td>52W High</td><td>348.15 -3.03%</td>"
    "<td>EPS/Sales Surpr.</td><td>6.77% -</td></tr>"
    "<tr><td>52W Low</td><td>243.42 38.62%</td>"
    "<td>Volatility</td><td>1.50% 2.00%</td></tr>"
    "<tr><td>ATR (14)</td><td>6.50</td><td>Change %</td><td>-0.61%</td></tr>"
)


def _current_snapshot_stock():
    # The current layout has no "52W Range" cell.
    html = (
        load_fixture("quote_aapl.html")
        .replace(
            "<tr><td>Optionable</td><td>Yes</td><td>Shortable</td><td>Yes</td></tr>",
            CURRENT_SNAPSHOT_ROWS,
        )
        .replace(
            "<tr><td>52W Range</td><td>164.08 - 260.10</td>"
            "<td>Volatility</td><td>1.50% 2.00%</td></tr>",
            "",
        )
    )
    use_session(FakeResponse(text=html))
    return finvizfinance("AAPL")


def test_fundament_splits_two_value_cells():
    fundament = _current_snapshot_stock().ticker_fundament(raw=False)
    assert fundament["Optionable"] is True
    assert fundament["Shortable"] is False
    assert fundament["Trades"] is None
    assert fundament["EPS past 3Y"] == pytest.approx(0.0689)
    assert fundament["EPS past 5Y"] == pytest.approx(0.1791)
    assert fundament["Dividend TTM Amount"] == pytest.approx(1.06)
    assert fundament["Dividend TTM %"] == pytest.approx(0.0031)
    assert fundament["52W High Price"] == pytest.approx(348.15)
    assert fundament["52W High %"] == pytest.approx(-0.0303)
    assert fundament["EPS Surprise"] == pytest.approx(0.0677)
    assert fundament["Sales Surprise"] is None
    # The combined keys stay for existing callers.
    assert fundament["EPS past 3/5Y"] == "6.89% 17.91%"
    assert fundament["Option/Short"] == "Yes / No"


def test_fundament_fills_legacy_keys():
    fundament = _current_snapshot_stock().ticker_fundament(raw=False)
    assert fundament["52W Range From"] == pytest.approx(243.42)
    assert fundament["52W Range To"] == pytest.approx(348.15)
    assert fundament["ATR"] == pytest.approx(6.5)
    assert fundament["Change"] == pytest.approx(-0.0061)


def test_fundament_legacy_keys_do_not_override_page_values():
    # The old layout still has its own 52W Range cell; that value wins.
    fundament = _stock("quote_aapl.html").ticker_fundament()
    assert fundament["52W Range From"] == "164.08"
    assert "ATR" not in fundament


def test_fundament_splits_two_value_cells_raw():
    fundament = _current_snapshot_stock().ticker_fundament()
    assert fundament["Optionable"] == "Yes"
    assert fundament["Shortable"] == "No"
    assert fundament["Dividend TTM %"] == "0.31%"
    assert fundament["52W High"] == "348.15 -3.03%"


def test_ticker_inside_trader():
    df = _stock("quote_aapl.html").ticker_inside_trader()
    assert df.iloc[0]["SEC Form 4 Link"] == "https://www.sec.gov/form4/1"
    assert df.iloc[0]["Insider_id"] == "1234"
    assert df.iloc[0]["#Shares"] == 1000


def test_ticker_full_info():
    info = _stock("quote_aapl.html").ticker_full_info()
    assert {"fundament", "ratings_outer", "news", "inside trader"}.issubset(info.keys())


def test_ticker_signal_wall_surfaces_not_silently_dropped():
    # First call builds the quote; the screener calls that follow hit the Wall.
    use_session([html_response("quote_aapl.html"), blocked_response()])
    stock = finvizfinance("AAPL")
    with pytest.raises(FinvizBlockedError):
        stock.ticker_signal()


def test_ticker_charts_invalid_timeframe():
    stock = _stock("quote_aapl.html")
    with pytest.raises(ValueError, match=r"Invalid timeframe 'dummy'"):
        stock.ticker_charts(timeframe="dummy")


# --- Statements (routes through the resilient JSON transport) ---------------


def test_statements_real():
    use_session(
        FakeResponse(
            content=b'{"currency": "USD", "data": {"2023": {"Revenue": "100"}}}'
        )
    )
    df = Statements().get_statements("AAPL")
    assert df is not None
    assert not df.empty
    # currency is exposed idiomatically in attrs, and labelled on the column axis
    assert df.attrs["currency"] == "USD"
    assert df.columns.name == "Currency: USD"


def test_statements_currency_missing_is_none_and_unlabelled():
    # finviz may omit currency; we must not render a misleading "Currency: None".
    use_session(FakeResponse(content=b'{"data": {"2023": {"Revenue": "100"}}}'))
    df = Statements().get_statements("AAPL")
    assert df.attrs["currency"] is None
    assert df.columns.name is None


def test_statements_wall_raises_blocked_error():
    use_session(blocked_response())
    with pytest.raises(FinvizBlockedError):
        Statements().get_statements("AAPL")


def test_statements_missing_data_raises_parse_error():
    use_session(FakeResponse(content=b"{}"))
    with pytest.raises(FinvizParseError):
        Statements().get_statements("AAPL")
