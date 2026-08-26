"""
.. module:: screener.ticker
   :synopsis: screen ticker table.

.. moduleauthor:: Tianning Li <ltianningli@gmail.com>
"""

from finvizfinance.screener.base import Base


class Ticker(Base):
    """Financial
    Getting information from the finviz screener ticker page.
    """

    v_page = 111

    def screener_view(
        self, order="Ticker", limit=-1, verbose=1, ascend=True, sleep_sec=1
    ):
        """Get screener stocks.

        Args:
            order(str): sort the list by the choice of order.
            limit(int): set the top k stocks of the screener.
            verbose(int): choice of visual the progress. 1 for visualize progress.
            ascend(bool): if True, the order is ascending.
            sleep_sec(int): sleep seconds for fetching each page.
        Returns:
            tickers(list): get all the tickers as list.
        """
        df = super().screener_view(
            order=order,
            limit=limit if limit != -1 else 100000,
            verbose=verbose,
            ascend=ascend,
            sleep_sec=sleep_sec,
        )
        if df is None:
            return None
        tickers = df["Ticker"].tolist()
        if limit != -1:
            tickers = tickers[:limit]
        return tickers
