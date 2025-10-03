from pydantic import BaseModel
from datetime import date

class Transaction(BaseModel):
    id: int
    date: date
    amount: int
    category_id: int
    account_id: int
    memo: str = ""
