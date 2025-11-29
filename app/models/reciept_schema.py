from pydantic import BaseModel, Field
from typing import List
from enum import Enum
# ─────────────────────────────────────────────────────────────
# ENUM: Categories
# ─────────────────────────────────────────────────────────────
class FoodCategory(str, Enum):
    FRUITS = "Fruits"
    VEGETABLES = "Vegetables"
    DAIRY = "Dairy"
    MEAT_POULTRY = "Meat & Poultry"
    FISH_SEAFOOD = "Fish & Seafood"
    GRAINS_CEREALS = "Grains & Cereals"
    SNACKS_PACKAGED = "Snacks & Packaged Foods"
    BEVERAGES = "Beverages"
    FROZEN_FOODS = "Frozen Foods"
    BAKERY = "Bakery"
    CONDIMENTS_SPICES = "Condiments & Spices"
    OTHER = "Other / Miscellaneous"


# ─────────────────────────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────────────────────────
class Product(BaseModel):
    name: str
    cost: float
    quantity: int
    total_cost: float


class Category(BaseModel):
    category_name: FoodCategory
    products: List[Product] = Field(default_factory=list)
    total_price: float


class ReceiptAnalysisResponse(BaseModel):
    store_name: str = "Unknown"
    receipt_date: str = "Unknown"
    categories: List[Category]
    grand_total: float
    tax_amount: float = 0.00
    subtotal: float = 0.00
