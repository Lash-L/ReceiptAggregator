from datetime import datetime, timedelta

import polars as pl

from receiptaggregator.models import ParsedReceipt
from receiptaggregator.string_similarity import jaro_distance


class ReceiptMatcher:
    """A class for matching receipts to existing transactions."""

    def __init__(self, transaction_csv: str) -> None:
        """Initialize the ReceiptMatcher.
        :param transaction_csv: The path to the csv file containing the transactions.
        """
        self.df = pl.read_csv(transaction_csv, try_parse_dates=True).with_row_count(
            "temp_id"
        )

    def match_receipt(self, receipt: ParsedReceipt, date_str: str) -> None:
        """Attempt to match a receipt to an existing transaction.
        :param receipt: The receipt to match.
        :param date_str: The date of the receipt.
        """
        # This all definitely isn't the most efficient way to do it - but in a real system you wouldn't be working with
        # csv anyways
        parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").date()
        date_start = parsed_date - timedelta(days=5)
        date_end = parsed_date + timedelta(days=5)

        condition = (
            (pl.col("Date").dt.date() >= date_start)
            & (pl.col("Date").dt.date() <= date_end)
            & (pl.col("Amount") == -receipt.total_billed)
        )
        potential_matches_df = self.df.filter(condition)
        high_similarity_matches = []
        for row in potential_matches_df.iter_rows(named=True):
            score = jaro_distance(receipt.merchant, row["Merchant"])
            if score >= 0.75:
                high_similarity_matches.append(row["temp_id"])
        if len(high_similarity_matches) == 0:
            return
        if len(high_similarity_matches) == 1:
            row_id_to_update = high_similarity_matches[0]
            receipt_classification_str = receipt.to_str()
            self.df = self.df.with_columns(
                pl.when(pl.col("temp_id") == row_id_to_update)
                .then(pl.lit("ReceiptAggregator"))
                .otherwise(pl.col("Tags"))
                .alias("Tags"),
                pl.when(pl.col("temp_id") == row_id_to_update)
                .then(
                    pl.when(pl.col("Notes").is_null() | (pl.col("Notes") == ""))
                    .then(pl.lit(receipt_classification_str))
                    .otherwise(
                        pl.col("Notes") + pl.lit("\n" + receipt_classification_str)
                    )
                )
                .otherwise(pl.col("Notes"))
                .alias("Notes"),
            )
        else:
            print()

    def update_csv(self, csv_path: str) -> None:
        """Dump the dataframe to a csv file.
        :param csv_path: The path to the csv file.
        """
        self.df.write_csv(csv_path)
