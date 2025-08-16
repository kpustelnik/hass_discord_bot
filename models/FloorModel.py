from pydantic import BaseModel
from typing import List

class FloorModel(BaseModel):
  id: str
  name: str
  areas: List[str]
  entities: List[str]