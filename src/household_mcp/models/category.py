from typing import Optional

from pydantic import BaseModel


class Category(BaseModel):
    id: int
    name: str
    parent_id: Optional[int] = None
