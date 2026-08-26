"""
.. module:: calendar
   :synopsis: calendar.

.. moduleauthor:: Tianning Li <ltianningli@gmail.com>
"""

import json
import pandas as pd
from finvizfinance.util import web_scrap


class Calendar:
    """Calendar
    Getting information from the finviz calendar page.
    """

    def __init__(self):
        """initiate module"""
        pass

    def calendar(self):
        """Get economic calendar table.

        Returns:
            df(pandas.DataFrame): economic calendar table
        """
        soup = web_scrap("https://finviz.com/calendar.ashx")
        # The calendar page is now a client-rendered React app; the entries
        # are shipped as JSON in the route-init-data script for hydration.
        data = json.loads(soup.find("script", id="route-init-data").text)
        entries = data["data"]["entries"]

        frame = []
        for entry in entries:
            info_dict = {
                "Datetime": entry["date"],
                "Release": entry["event"],
                "Impact": entry["importance"],
                "For": entry["reference"],
                "Actual": entry["actual"],
                "Expected": entry["forecast"],
                "Prior": entry["previous"],
            }
            frame.append(info_dict)
        return pd.DataFrame(frame)
