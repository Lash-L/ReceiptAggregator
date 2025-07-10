from google.genai import Client


class RuleBasedClassifier:
    """Classify an email as a receipt or not a receipt."""

    def __init__(self) -> None:
        """Initialize the RuleBasedClassifier."""
        self._rules = {
            "subject": {
                "receipt": 50,
                "invoice": 50,
                "your order": 25,
                "order confirmation": 50,
                "shipped": -50,
                "offer": -30,
                "return": -35,
                "warranty": -35,
                "rejoin": -10,
                "coming soon": -30,
                "delivered": -20,
                "on the way": -15,
            },
            "body": {
                "receipt": 30,
                "order": 10,
                "order #": 30,
                "order number": 30,
                "$": 10,
                "total amount": 15,
                "total billed": 15,
                "unsubscribe": -5,
                "offer": -15,
                "shipment": -10,
                "on the way": -10,
                "tracking number": -10,
                "limited time": -10,
                "quantity:": 15,
                "subtotal": 20,
                "billing information": 15,
            },
        }

    def score_email(self, email: dict) -> float:
        """Score an email based on the rules.
        :param email: The email to score.
        """
        score = 0
        for subject_rule, value in self._rules["subject"].items():
            if subject_rule in email["Subject"].lower():
                score += value
        for body_rule, value in self._rules["body"].items():
            if body_rule in email["Body"].lower():
                score += value
        return score

    def classify_email(self, email: dict) -> bool:
        """Classify an email as a receipt or not a receipt.
        :param email: The email to classify.
        """
        score = self.score_email(email)
        return score >= 55


class GeminiClassifier:
    """Classify an email as a receipt or not a receipt."""

    def __init__(self, api_key: str) -> None:
        """Initialize the GeminiClassifier."""
        self._key = api_key

    async def gemini_classification(self, email: dict) -> bool:
        """Classify an email as a receipt or not a receipt.
        :param email: The email to classify.
        """
        client = Client(api_key=self._key)
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "You are a Email Classifier. You will receieve a email and "
                "you should state if it is RECEIPT or NOT RECEIPT. "
                "A Receipt should contain the items that were purchased and their individual prices, as well as the toatl price."
                "Give NO other response."
                "Examples:"
                "Receipts:"
                "Your order has been received."
                "Thanks for your order"
                "Order #532523"
                "Receipt from ..."
                ""
                "Not Receipts:"
                "Your order has been shipped!"
                "Place your order today!"
                f"The user's email is {email}"
            ],
        )
        classification = response.text
        # Note: This should likely use a response schema.
        return classification == "RECEIPT"
