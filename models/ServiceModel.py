from pydantic import BaseModel
from typing import List, Dict, Optional, Dict

class ServiceFieldSelectorText(BaseModel):
  multiple: Optional[bool] = None # Submitted as List[str] if multiple

class ServiceFieldSelectorNumber(BaseModel):
  mode: Optional[str] = None
  step: Optional[str | float | int] = None
  min: Optional[float | int] = None
  max: Optional[float | int] = None
  unit_of_measurement: Optional[str] = None
  unit: Optional[str] = None

class ServiceFieldSelectorEntity(BaseModel):
  multiple: Optional[bool] = None # Submitted as List[str] if multiple
  integration: Optional[str] = None
  domain: Optional[str] = None
  
class ServiceFieldSelectorDevice(BaseModel):
  multiple: Optional[bool] = None # Submitted as List[str] if multiple
  integration: Optional[str] = None
  domain: Optional[str] = None

class ServiceFieldSelectorSelect(BaseModel):
  options: List[str]
  translation_key: Optional[str] = None
  multiple: Optional[bool] = None # Submitted as List[str] if multiple

class ServiceFieldSelectorBoolean(BaseModel):
  pass

class ServiceFieldSelectorTheme(BaseModel):
  include_default: Optional[bool] = None

class ServiceFieldSelectorConstant(BaseModel):
  label: str
  value: bool

class ServiceFieldSelectorObject(BaseModel):
  pass

class ServiceFieldSelector(BaseModel):
  text: Optional[ServiceFieldSelectorText] = None
  config_entry: Optional[ServiceFieldSelectorText] = None # Treat like text
  conversation_agent: Optional[ServiceFieldSelectorText] = None # Treat like text
  number: Optional[ServiceFieldSelectorNumber] = None
  duration: Optional[ServiceFieldSelectorText] = None # Treat like text
  entity: Optional[ServiceFieldSelectorEntity] = None
  select: Optional[ServiceFieldSelectorSelect] = None
  boolean: Optional[ServiceFieldSelectorBoolean] = None
  theme: Optional[ServiceFieldSelectorTheme] = None
  color_temp: Optional[ServiceFieldSelectorNumber] = None
  datetime: Optional[ServiceFieldSelectorText] = None # Treat like text
  time: Optional[ServiceFieldSelectorText] = None # Treat like text
  date: Optional[ServiceFieldSelectorText] = None # Treat like text
  statistic: Optional[ServiceFieldSelectorEntity] = None # Treat like entities
  object: Optional[ServiceFieldSelectorObject] = None
  template: Optional[ServiceFieldSelectorText] = None # Treat like text
  color_rgb: Optional[ServiceFieldSelectorObject] = None # Treat like object
  device: Optional[ServiceFieldSelectorDevice] = None # Treat like entity
  icon: Optional[ServiceFieldSelectorText] = None # Treat like text

class ServiceFieldFilter(BaseModel):
  supported_features: Optional[List[int]] = None # Bitset (any needs to be supported)
  attribute: Optional[Dict[str, List[str] | str]] = None

class ServiceField(BaseModel):
  description: Optional[str] = None
  example: Optional[str | int | float | bool | List[str] | Dict] = None # Or object (recorder.get_statistics)
  default: Optional[str | int | float | bool | List[str] | Dict] = None
  name: Optional[str] = None
  required: Optional[bool] = None
  advanced: Optional[bool] = None
  selector: Optional[ServiceFieldSelector] = None # Field is not displayed if it's missing (only available in YAML mode)
  filter: Optional[ServiceFieldFilter] = None

class ServiceFieldCollection(BaseModel):
  collapsed: Optional[bool] = None
  fields: Dict[str, ServiceField]
  # Should they be sent in different format?

class ServiceTargetDevice(BaseModel):
  pass # Not really sure what it's used for - it's only in one place (reload config entries)

class ServiceTargetEntity(BaseModel):
  domain: Optional[List[str]] = None
  supported_features: Optional[List[int]] = None # Bitset flags
  integration: Optional[str] = None
  # `area_id``, `device_id``, `entity_id``, label can be passed as a target

class ServiceTarget(BaseModel):
  device: Optional[ServiceTargetDevice] = None # Always has 1 item if available
  entity: Optional[ServiceTargetEntity] = None # Always has 1 item if available

class ServiceResponse(BaseModel):
  optional: Optional[bool] = None

class ServiceModel(BaseModel):
  name: str
  description: Optional[str] = None
  fields: Optional[Dict[str, ServiceField | ServiceFieldCollection]] = None
  target: Optional[ServiceTarget] = None
  response: Optional[ServiceResponse] = None

class DomainModel(BaseModel):
  domain: str
  services: Dict[str, ServiceModel]