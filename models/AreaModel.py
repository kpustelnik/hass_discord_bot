from pydantic import BaseModel
from typing import List

class AreaModel(BaseModel):
  id: str
  name: str
  entities: List[str]
  devices: List[str]