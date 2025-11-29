from pydantic import BaseModel
from typing import List, Optional

class Item(BaseModel):
    name: str
    price: float
    quantity: int
    category: str

class Receipt(BaseModel):
    store_name: str
    store_location: Optional[str]
    date: str
    total: float
    items: List[Item]
