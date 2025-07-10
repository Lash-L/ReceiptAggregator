import ollama

from receiptaggregator.models import ParsedReceipt


class OllamaReceiptExtractor:
    """Extract data from receipts using an Ollama model."""

    def __init__(self, ollama_client: ollama.Client, model: str) -> None:
        """Initialize the OllamaReceiptExtractor.
        :param ollama_client: The ollama client to use.
        :param model: The model to use.
        """
        self.ollama_client = ollama_client
        self._model = model

    def extract_data(self, receipt: dict) -> ParsedReceipt:
        """Extract the data from a receipt using an Ollama model.
        :param receipt: The receipt to extract data from.
        """
        # This could be async, but my machine can barely handle one at a time.
        response = self.ollama_client.chat(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": """
                                You are responsible for extracting the items purchased from a receipt, the total cost, and the final billed amount.
                                Your output MUST be in a JSON format that adheres to the schema.
                                - "total_cost" is the sum of all item costs before any promotions or gift cards.
                                - "total_billed" is the final amount after all adjustments.
                                - "item_description" can be an empty string if not present on the receipt.
                                """,
                },
                {
                    "role": "user",
                    "content": f"Please extract the information from this receipt:\n\n{receipt}",
                },
            ],
            format=ParsedReceipt.model_json_schema(),
        )
        return ParsedReceipt.model_validate_json(response.message.content)
