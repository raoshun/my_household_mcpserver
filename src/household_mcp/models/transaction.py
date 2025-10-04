from datetime import date

from pydantic import BaseModel


class Transaction(BaseModel):
    id: int
    date: date
    amount: int
    category_id: int
    account_id: int
    memo: str = ""
