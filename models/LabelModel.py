from pydantic import BaseModel
from typing import List, Optional

class LabelModel(BaseModel):
  id: str
  name: str
  description: Optional[str]
  areas: List[str]
  devices: List[str]
  entities: List[str]