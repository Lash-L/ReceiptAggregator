from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    """An item purchased in a receipt."""

    item_name: str = Field(description="The name of the item purchased.")
    item_cost: float = Field(description="The cost of the item.")
    item_description: str | None = Field(
        description="The description of the item (e.g., color, size).", default=None
    )
    item_quantity: int = Field(
        description="The quantity of the item purchased.", default=1
    )

    def to_str(self) -> str:
        """Represent a str of the ReceiptItem."""
        return f"{self.item_quantity}x {self.item_name} - ${self.item_cost} "


class ParsedReceipt(BaseModel):
    """Extracted data from a receipt."""

    merchant: str = Field(description="The merchant name of the receipt.")
    total_cost: float = Field(
        description="The total cost of the receipt before any adjustments (Subtotal)."
    )
    total_billed: float = Field(
        description="The final amount charged to a credit card or other external payment method after all adjustments."
    )
    payment_method: str | None = Field(
        description="The last four digits of the card used to pay the final billed amount.",
        default=None,
    )
    items: list[ReceiptItem] = Field(
        description="A list of items purchased in the receipt."
    )

    def to_str(self) -> str:
        """Represent a str of the ParsedReceipt."""
        res = f"Total Cost: {self.total_cost} - Total Billed: {self.total_billed} \n"
        for item in self.items:
            # TODO: Could be fancy here and handle things like discounts
            res += item.to_str() + "\n"
        return res
