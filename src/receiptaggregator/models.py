from pydantic import BaseModel, Field


class ReceiptItem(BaseModel):
    """An item purchased in a receipt."""

    item_name: str = Field(description="The name of the item purchased.")
    item_cost: float = Field(description="The cost of the item.")
    item_description: str | None = Field(
        description="The description of the item (If it exists).", default=None
    )
    item_quantity: int = Field(
        description="The quantity of the item purchased.", default=1
    )
    payment_method: str | None = Field(
        description="The payment method used for the purchase if it is found. (i.e. Visa 5320)."
    )

    def to_str(self) -> str:
        """Represent a str of the ReceiptItem."""
        return f"{self.item_quantity}x {self.item_name} - ${self.item_cost} "


class ParsedReceipt(BaseModel):
    """Extracted data from a receipt."""

    merchant: str = Field(
        description="The merchant name of the receipt (If it can be found)."
    )
    total_cost: float = Field(
        description="The total cost of the receipt before any adjustments."
    )
    total_billed: float = Field(
        description="The total amount billed after all adjustments. this is what the user should see on their credit card statement (i.e. total cost - gift card used or discount used). Make sure it is not the subtotal, but the total."
    )
    items: list[ReceiptItem] = Field(
        description="A list of items purchased in the receipt."
    )

    def to_str(self) -> str:
        """Represent a str of the ParsedReceipt.."""
        res = ""
        for item in self.items:
            # TODO: Could be fancy here and handle things like discounts
            res += item.to_str() + ","
        return res[:-1]  # easy remove last ,
