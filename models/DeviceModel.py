from pydantic import BaseModel
from typing import List, Optional

class DeviceModel(BaseModel):
  id: str
  area_id: Optional[str] = None
  name: str
  name_by_user: Optional[str] = None
  entities: List[str]
  manufacturer: Optional[str] = None
  model: Optional[str] = None
  model_id: Optional[str] = None
  serial_number: Optional[str] = None
  hw_version: Optional[str] = None
  sw_version: Optional[str] = None