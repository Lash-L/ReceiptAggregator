import os
from datetime import datetime, timedelta
from typing import Any

import polars as pl
from dotenv import load_dotenv
from gql import gql
from monarchmoney import MonarchMoney
from monarchmoney.monarchmoney import DEFAULT_RECORD_LIMIT

from receiptaggregator.models import ParsedReceipt
from receiptaggregator.string_similarity import jaro_distance


class CsvReceiptMatcher:
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
            # Including the from email here as well may help improve results.
            score = jaro_distance(receipt.merchant.lower(), row["Merchant"].lower())
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


class OverLoadedMonarchApi(MonarchMoney):
    async def get_transactions(
        self,
        limit: int = DEFAULT_RECORD_LIMIT,
        offset: int | None = 0,
        start_date: str | None = None,
        end_date: str | None = None,
        search: str = "",
        category_ids: list[str] = [],
        account_ids: list[str] = [],
        tag_ids: list[str] = [],
        has_attachments: bool | None = None,
        has_notes: bool | None = None,
        hidden_from_reports: bool | None = None,
        is_split: bool | None = None,
        is_recurring: bool | None = None,
        imported_from_mint: bool | None = None,
        synced_from_institution: bool | None = None,
        amount: float | None = None,
    ) -> dict[str, Any]:
        """Gets transaction data from the account.

        :param limit: the maximum number of transactions to download, defaults to DEFAULT_RECORD_LIMIT.
        :param offset: the number of transactions to skip (offset) before retrieving results.
        :param start_date: the earliest date to get transactions from, in "yyyy-mm-dd" format.
        :param end_date: the latest date to get transactions from, in "yyyy-mm-dd" format.
        :param search: a string to filter transactions. use empty string for all results.
        :param category_ids: a list of category ids to filter.
        :param account_ids: a list of account ids to filter.
        :param tag_ids: a list of tag ids to filter.
        :param has_attachments: a bool to filter for whether the transactions have attachments.
        :param has_notes: a bool to filter for whether the transactions have notes.
        :param hidden_from_reports: a bool to filter for whether the transactions are hidden from reports.
        :param is_split: a bool to filter for whether the transactions are split.
        :param is_recurring: a bool to filter for whether the transactions are recurring.
        :param imported_from_mint: a bool to filter for whether the transactions were imported from mint.
        :param synced_from_institution: a bool to filter for whether the transactions were synced from an institution.
        """
        query = gql(
            """
          query GetTransactionsList($offset: Int, $limit: Int, $filters: TransactionFilterInput, $orderBy: TransactionOrdering) {
            allTransactions(filters: $filters) {
              totalCount
              results(offset: $offset, limit: $limit, orderBy: $orderBy) {
                id
                ...TransactionOverviewFields
                __typename
              }
              __typename
            }
            transactionRules {
              id
              __typename
            }
          }

          fragment TransactionOverviewFields on Transaction {
            id
            amount
            pending
            date
            hideFromReports
            plaidName
            notes
            isRecurring
            reviewStatus
            needsReview
            attachments {
              id
              extension
              filename
              originalAssetUrl
              publicId
              sizeBytes
              __typename
            }
            isSplitTransaction
            createdAt
            updatedAt
            category {
              id
              name
              __typename
            }
            merchant {
              name
              id
              transactionsCount
              __typename
            }
            account {
              id
              displayName
              __typename
            }
            tags {
              id
              name
              color
              order
              __typename
            }
            __typename
          }
        """
        )

        variables = {
            "offset": offset,
            "limit": limit,
            "orderBy": "date",
            "filters": {
                "search": search,
                "categories": category_ids,
                "accounts": account_ids,
                "tags": tag_ids,
            },
        }

        # If bool filters are not defined (i.e. None), then it should not apply the filter
        if has_attachments is not None:
            variables["filters"]["hasAttachments"] = has_attachments

        if has_notes is not None:
            variables["filters"]["hasNotes"] = has_notes

        if hidden_from_reports is not None:
            variables["filters"]["hideFromReports"] = hidden_from_reports

        if is_recurring is not None:
            variables["filters"]["isRecurring"] = is_recurring

        if is_split is not None:
            variables["filters"]["isSplit"] = is_split

        if imported_from_mint is not None:
            variables["filters"]["importedFromMint"] = imported_from_mint

        if synced_from_institution is not None:
            variables["filters"]["syncedFromInstitution"] = synced_from_institution

        if start_date and end_date:
            variables["filters"]["startDate"] = start_date
            variables["filters"]["endDate"] = end_date

        if amount:
            variables["filters"]["absAmountLte"] = amount
            variables["filters"]["absAmountGte"] = amount

        elif bool(start_date) != bool(end_date):
            raise Exception(
                "You must specify both a startDate and endDate, not just one of them."
            )

        return await self.gql_call(
            operation="GetTransactionsList", graphql_query=query, variables=variables
        )


class ApiReceiptMatcher:
    """A class for matching receipts to existing transactions."""

    def __init__(self) -> None:
        """Initialize the ReceiptMatcher."""
        self.api = OverLoadedMonarchApi()
        self._receipt_aggregator_tag = None
        self._retail_sync_tag = None

    async def login(self) -> None:
        """Login to Monarch's api."""
        load_dotenv()
        email = os.getenv("MONARCH_EMAIL")
        password = os.getenv("MONARCH_PASSWORD")
        mfa_key = os.getenv("MONARCH_MFA_SECRET")

        await self.api.login(
            email, password, mfa_secret_key=mfa_key, use_saved_session=False
        )

    async def setup(self) -> None:
        """Do first time setup to get needed tags."""
        tags = await self.api.get_transaction_tags()
        for tag in tags["householdTransactionTags"]:
            if tag["name"] == "ReceiptAggregator":
                self._receipt_aggregator_tag = tag["id"]
            if tag["name"] == "Retail Sync":
                self._retail_sync_tag = tag["id"]
        if self._receipt_aggregator_tag is None:
            res = await self.api.create_transaction_tag("ReceiptAggregator", "#008080")
            self._receipt_aggregator_tag = res["createTransactionTag"]["tag"]["id"]

    async def match_receipt(self, receipt: ParsedReceipt, date_str: str) -> None:
        """Attempt to match a receipt to an existing transaction.
        :param receipt: The receipt to match.
        :param date_str: The date of the receipt.
        """
        parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z").date()
        date_start = parsed_date - timedelta(days=5)
        date_end = parsed_date + timedelta(days=5)

        transactions = await self.api.get_transactions(
            start_date=date_start.isoformat(),
            end_date=date_end.isoformat(),
            amount=receipt.total_billed,
        )
        high_similarity_matches = []
        for transaction in transactions["allTransactions"]["results"]:
            # Including the from email here as well may help improve results.
            score = jaro_distance(
                receipt.merchant.lower(), transaction["merchant"]["name"].lower()
            )
            if score >= 0.75:
                high_similarity_matches.append(transaction)
        if len(high_similarity_matches) == 1:
            match = high_similarity_matches[0]
            if match["tags"]:
                for tag in match["tags"]:
                    if tag["name"] in {"ReceiptAggregator", "Retail Sync"}:
                        return
            if self._receipt_aggregator_tag not in match["tags"]:
                await self.api.set_transaction_tags(
                    match["id"], match["tags"] + [self._receipt_aggregator_tag]
                )
                await self.api.update_transaction(
                    match["id"],
                    notes=match["notes"] if match["notes"] else "" + receipt.to_str(),
                )
                print(f"Updated {receipt.merchant}")
