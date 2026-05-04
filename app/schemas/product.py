from pydantic import BaseModel
from uuid import UUID


class ProductOut(BaseModel):
    id: UUID
    name: str
    price: float
    color: str | None
    occasion: str | None
    stock: int
    image_url: str | None

    class Config:
        from_attributes = True