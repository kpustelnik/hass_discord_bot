from pydantic import BaseModel
from typing import List

class DeviceModel(BaseModel):
  id: str
  name: str
  entities: List[str]