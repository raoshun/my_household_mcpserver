from pydantic import BaseModel

class Metric(BaseModel):
    name: str
    description: str
    formula: str
