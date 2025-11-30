import base64
from enum import Enum
from typing import List
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field
from app.config import settings

load_dotenv()


from app.models.reciept_schema import ReceiptAnalysisResponse


# ─────────────────────────────────────────────────────────────
# LLM Prompt
# ─────────────────────────────────────────────────────────────
RECEIPT_CATEGORIZATION_PROMPT = """
You are an expert at analyzing grocery receipts and categorizing food items. 

Your Task:
Analyze the receipt image and extract all products, then categorize each product into one of the predefined categories.

Rules:
1. Extract EVERY item line including items with weights, specials, or multi-buy.
2. If quantity missing → assume "1".
3. If cost missing → use total_cost for both.
4. Keep units inside the product name (e.g., “200g”, “1L”, “500 ml”).
5. Prices must always be string numbers with 2 decimal places.
6. DO NOT invent items. Only extract what's visible.
7. Extract store name, date, subtotal, tax, and grand total.
8. Return ONLY valid JSON following the schema. No explanations.
"""


# ─────────────────────────────────────────────────────────────
# Receipt Scanner Class
# ─────────────────────────────────────────────────────────────
class ReceiptScanner:
    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY missing")

        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY )
        self.model = "gpt-4o"


    # Encode image to Base64
    def encode_image(self, path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    # ─────────────────────────────────────────────────────────
    # Run Analysis
    # ─────────────────────────────────────────────────────────
    def scan_receipt(self, image_path, user_id):
        image_base64 = self.encode_image(image_path)

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": RECEIPT_CATEGORIZATION_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this receipt image."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "high"
                            }
                        },
                    ],
                },
            ],
            temperature=0,
            response_format=ReceiptAnalysisResponse,
        )

        parsed = response.choices[0].message.parsed
        data = parsed.dict()


        grand_total = data["grand_total"]
        total_tax = data.get("tax_amount", 0.00)

        for category in data["categories"]:
            total_price = category['total_price']
            tax_amount = total_tax * total_price / grand_total
            category['tax_amount'] = round(tax_amount, 2)
            category['total_price_incl_tax'] = round(total_price + tax_amount, 2)
    
        # Add metadata
        data["user_id"] = user_id
        data["scan_timestamp"] = datetime.now().isoformat()

        return data

    