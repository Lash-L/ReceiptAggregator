import asyncio

import ollama

from receiptaggregator import ParsedReceipt
from receiptaggregator.eml_loader import parse_directory
from receiptaggregator.invoice_classification import (
    RuleBasedClassifier,
)
from receiptaggregator.receipt_extractor import OllamaReceiptExtractor
from receiptaggregator.receipt_matcher import ReceiptMatcher


async def main() -> None:
    """Run the entire pipeline."""
    email_files = parse_directory("eml_files")
    # gemini_classifier = GeminiClassifier("my_api")
    # classifications = await asyncio.gather(
    #     *(gemini_classifier.gemini_classification(email) for email in email_files)
    # )
    rule_classifier = RuleBasedClassifier()
    rule_classification = [
        rule_classifier.classify_email(email) for email in email_files
    ]
    receipts = []
    for email, rule_class in zip(email_files, rule_classification):
        if rule_class:
            receipts.append(email)
    ollama_client = ollama.Client(host="OLLAMA_URL")
    rec_extract = OllamaReceiptExtractor(ollama_client, "gemma3:4b")

    parsed_receipts: list[ParsedReceipt | None] = []
    for receipt in receipts:
        try:
            parsed_receipts.append(rec_extract.extract_data(receipt))
        except Exception:
            parsed_receipts.append(None)
    rm = ReceiptMatcher("monarch_csv.csv")
    for receipt, email in zip(parsed_receipts, receipts):
        if receipt is not None:
            rm.match_receipt(receipt, email["Date"])
    rm.update_csv("monarch_csv_updated.csv")


if __name__ == "__main__":
    asyncio.run(main())
