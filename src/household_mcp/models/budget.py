from pydantic import BaseModel


class Budget(BaseModel):
    category_id: int
    amount: int
    period: str
