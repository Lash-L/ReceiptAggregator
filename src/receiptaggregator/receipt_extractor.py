import ollama
from google.genai import Client, types

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
        system_prompt = """
You are an expert data extraction agent. Your task is to meticulously extract information from a user-provided email receipt and format it as a JSON object that adheres to the provided schema.

Follow these rules precisely:
1.  **`merchant`**: Extract the merchant's name. It is usually found in the 'From' field or prominently at the top/bottom of the email (e.g., 'Bombas').
2.  **`total_cost`**: This is the sum of all item costs before any discounts or other adjustments. Find the value on the 'Subtotal' line.
3.  **`total_billed`**: This is the final amount charged to an external payment method like a credit card. To calculate this, find the final 'Total' and subtract any 'Gift card' amounts. If a Visa/Mastercard/Amex payment is explicitly listed, use that value. This is NOT the 'Subtotal' and it is NOT the final 'Total' if a gift card was used.
4.  **`payment_method`**: This is the identifier for the external payment method used for the `total_billed` amount. If a credit card was used, this should be the last four digits of the card number (e.g., '7213').
5.  **`items`**: This is a list of all purchased items.
    *   **`item_name`**: The primary name of the product (e.g., "Men's Running Ankle Sock 6-Pack").
    *   **`item_cost`**: The final price for that item line after any item-specific discounts. Use the final price listed for the item, not a crossed-out original price.
    *   **`item_description`**: A single string containing additional details. Look for 'Color' and 'Size' lines immediately following the item name and combine them, separated by a newline.
    *   **`item_quantity`**: The quantity for that item line.

    Here is an example of perfect execution:

    <example>
    <receipt_text>
    Order Summary
    Men's Running Ankle Sock 6-Pack
    Color: Navy red mix
    Size: L
    Unit Price: $95.00
    Subtotal: $149.00
    Order Discount: -$29.80
    Total: $126.35
    Gift card: $121.88
    Visa (ending in 5478): $4.47
    </receipt_text>
    <json_output>
    {
      "merchant": "Bombas",
      "total_cost": 149.00,
      "total_billed": 4.47,
      "items": [
        {
          "item_name": "Men's Running Ankle Sock 6-Pack",
          "item_cost": 95.00,
          "item_description": "Color: Navy red mix, Size: L",
          "item_quantity": 1
        }
      ],
      "payment_method": "5478"
    }
    </json_output>
    </example>

'''
### END EXAMPLE ###

Now, extract the information from the following receipt. Your output MUST be a single, valid JSON object and nothing else.
    """
        response = self.ollama_client.chat(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": f"Please extract the information from this receipt:\n\n{receipt}",
                },
            ],
            format=ParsedReceipt.model_json_schema(),
        )
        return ParsedReceipt.model_validate_json(response["message"]["content"])


class GeminiReceiptExtractor:
    """Extract data from receipts using a Gemini model."""

    def __init__(self, api_key: str, model: str) -> None:
        """Initialize the GeminiReceiptExtractor.
        :param gemini_client: The gemini client to use.
        :param model: The model to use.
        """
        self._client = Client(api_key=api_key)
        self._model = model

    def extract_data(self, receipt: dict) -> ParsedReceipt:
        """Extract the data from a receipt using an Gemini model.
        :param receipt: The receipt to extract data from.
        """
        # The new, highly-detailed system prompt
        system_prompt = """
You are an expert data extraction agent. Your task is to meticulously extract information from a user-provided email receipt and format it as a JSON object that adheres to the provided schema.

Follow these rules precisely:
1.  **`merchant`**: Extract the merchant's name. It is usually found in the 'From' field or prominently at the top/bottom of the email (e.g., 'Bombas').
2.  **`total_cost`**: This is the sum of all item costs before any discounts or other adjustments. Find the value on the 'Subtotal' line.
3.  **`total_billed`**: This is the final amount charged to an external payment method like a credit card. To calculate this, find the final 'Total' and subtract any 'Gift card' amounts. If a Visa/Mastercard/Amex payment is explicitly listed, use that value. This is NOT the 'Subtotal' and it is NOT the final 'Total' if a gift card was used.
4.  **`payment_method`**: This is the identifier for the external payment method used for the `total_billed` amount. If a credit card was used, this should be the last four digits of the card number (e.g., '7213').
5.  **`items`**: This is a list of all purchased items.
    *   **`item_name`**: The primary name of the product (e.g., "Men's Running Ankle Sock 6-Pack").
    *   **`item_cost`**: The final price for that item line after any item-specific discounts. Use the final price listed for the item, not a crossed-out original price.
    *   **`item_description`**: A single string containing additional details. Look for 'Color' and 'Size' lines immediately following the item name and combine them, separated by a newline.
    *   **`item_quantity`**: The quantity for that item line.

    Here is an example of perfect execution:

    <example>
    <receipt_text>
    Order Summary
    Men's Running Ankle Sock 6-Pack
    Color: Navy red mix
    Size: L
    Unit Price: $95.00
    Subtotal: $149.00
    Order Discount: -$29.80
    Total: $126.35
    Gift card: $121.88
    Visa (ending in 5478): $4.47
    </receipt_text>
    <json_output>
    {
      "merchant": "Bombas",
      "total_cost": 149.00,
      "total_billed": 4.47,
      "items": [
        {
          "item_name": "Men's Running Ankle Sock 6-Pack",
          "item_cost": 95.00,
          "item_description": "Color: Navy red mix, Size: L",
          "item_quantity": 1
        }
      ],
      "payment_method": "5478"
    }
    </json_output>
    </example>

'''
### END EXAMPLE ###

Now, extract the information from the following receipt. Your output MUST be a single, valid JSON object and nothing else.
    """
        response = self._client.models.generate_content(
            model=self._model,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_schema=ParsedReceipt.model_json_schema(),
            ),
            contents=[
                types.Part.from_text(
                    text=f"Please extract the information from this receipt:\n\n{receipt}"
                )
            ],
        )
        try:
            return ParsedReceipt.model_validate_json(
                response.text.strip("```json").strip("```")
            )
        except Exception:
            print(response.text)
            raise
