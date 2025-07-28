from pydantic import BaseModel, PlainSerializer
from datetime import datetime
from typing import Annotated, Optional, Dict, Any

DatetimeIsoField = Annotated[
    datetime,
    PlainSerializer(lambda x: x.isoformat(), return_type=str, when_used="json"),
]

class EntityContext(BaseModel):
  id: str
  parent_id: Optional[str] = None
  user_id: Optional[str] = None

class EntityModel(BaseModel):
  entity_id: str

  last_changed: Optional[DatetimeIsoField] = None
  last_updated: Optional[DatetimeIsoField] = None
  last_reported: Optional[DatetimeIsoField] = None

  state: str
  context: Optional[EntityContext] = None
  attributes: Dict[str, Any]