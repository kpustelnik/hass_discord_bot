from __future__ import annotations
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from enum import Enum

# Sources:
# https://developers.home-assistant.io/docs/dev_101_services/
# https://www.home-assistant.io/docs/blueprint/selectors/#date-selector
# https://github.com/home-assistant/frontend/blob/dev/src/data/selector.ts
# https://github.com/home-assistant/home-assistant-js-websocket/blob/master/lib/types.ts

number = int | float

# Helpers
class ServiceFieldSelectorEntityFilter(BaseModel, extra='forbid'):
  integration: Optional[str] = None
  domain: Optional[List[str] | str] = None
  device_class: Optional[List[str] | str] = None
  supported_features: Optional[List[int] | int] = None

class ServiceFieldSelectorDeviceFilter(BaseModel, extra='forbid'):
  integration: Optional[str] = None
  manufacturer: Optional[str] = None
  model: Optional[str] = None
  model_id: Optional[str] = None

class CropOptions(BaseModel, extra='forbid'):
  round: bool
  type: Optional[str] # "image/jpeg" / "image/png"
  quality: Optional[number] = None
  aspectRatio: Optional[number] = None

class SelectBoxOptionImage(BaseModel, extra='forbid'):
  src: str
  src_dark: Optional[str] = None
  flip_rtl: Optional[bool] = None
  
class ServiceFieldSelectorNumberMode(str, Enum):
  BOX = 'box'
  SLIDER = 'slider'

class ServiceFieldSelectorSelectMode(str, Enum):
  LIST = 'list'
  DROPDOWN = 'dropdown'
  BOX = 'box'

class ServiceFieldSelectorQRCodeErrorCorrectionLevel(str, Enum):
  LOW = 'low'
  MEDIUM = 'medium'
  QUARTILE = 'quartile'
  HIGH = 'high'

class ServiceFieldSelectorTextType(str, Enum):
  NUMBER = 'number'
  TEXT = 'text'
  SEARCH = 'search'
  TEL = 'tel'
  URL = 'url'
  EMAIL = 'email'
  PASSWORD = 'password'
  DATE = 'date'
  MONTH = 'month'
  WEEK = 'week'
  TIME = 'time'
  DATETIME_LOCAL = 'datetime-local'
  COLOR = 'color'

# Selectors
class ServiceFieldSelectorAction(BaseModel, extra='forbid'): # not supported (would require selecting target etc. basing on the action selected)
  optionsInSidebar: Optional[bool] = None

class ServiceFieldSelectorAddon(BaseModel, extra='forbid'): # not supported (no HACS to test)
  name: Optional[str] = None
  slug: Optional[str] = None

class ServiceFieldSelectorArea(BaseModel, extra='forbid'):
  entity: Optional[List[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter] = None
  device: Optional[List[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter] = None
  multiple: Optional[bool] = None

class ServiceFieldSelectorAreasDisplay(BaseModel, extra='forbid'): # not supported
  pass

class ServiceFieldSelectorAttribute(BaseModel, extra='forbid'):
  entity_id: Optional[List[str] | str] = None
  hide_attributes: Optional[List[str]] = None

class ServiceFieldSelectorAssistPipeline(BaseModel, extra='forbid'): # not supported
  include_last_used: Optional[bool] = None

class ServiceFieldSelectorBackground(BaseModel, extra='forbid'): # not supported
  original: Optional[bool] = None
  crop: Optional[CropOptions] = None

class ServiceFieldSelectorBackupLocation(BaseModel, extra='forbid'): # not supported
  pass

class ServiceFieldSelectorBoolean(BaseModel, extra='forbid'):
  pass

class ServiceFieldSelectorButtonToggle(BaseModel, extra='forbid'):
  options: List[str | ServiceFieldSelectorSelectOption]
  translation_key: Optional[str]
  sort: Optional[bool]

class ServiceFieldSelectorColorRGB(BaseModel, extra='forbid'):
  pass

class ServiceFieldSelectorColorTemp(BaseModel, extra='forbid'):
  unit: Optional[str] = None
  min: Optional[number] = None
  max: Optional[number] = None
  min_mireds: Optional[number] = None
  max_mireds: Optional[number] = None

class ServiceFieldSelectorCondition(BaseModel, extra='forbid'): # not supported
  optionsInSidebar: Optional[bool] = None

class ServiceFieldSelectorConfigEntry(BaseModel, extra='forbid'): # not supported
  integration: Optional[str] = None
  
class ServiceFieldSelectorConstant(BaseModel, extra='forbid'):
  label: Optional[str] = None
  value: str | number | bool
  translation_key: Optional[str] = None

class ServiceFieldSelectorConversationAgent(BaseModel, extra='forbid'):
  language: Optional[str] = None # filtering by language not supported

class ServiceFieldSelectorCountry(BaseModel, extra='forbid'):
  countries: List[str] = None
  no_sort: Optional[bool] = None

class ServiceFieldSelectorDate(BaseModel, extra='forbid'):
  pass

class ServiceFieldSelectorDateTime(BaseModel, extra='forbid'):
  pass

class ServiceFieldSelectorDevice(BaseModel, extra='forbid'):
  entity: Optional[List[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter] = None # Only devices having >= 1 matching entity will be displayed
  filter: Optional[List[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter] = None
  multiple: Optional[bool] = None # Submitted as List[str] if multiple

class ServiceFieldSelectorDeviceLegacy(ServiceFieldSelectorDevice):
  integration: Optional[str] = None
  manufacturer: Optional[str] = None
  model: Optional[str] = None
  
class ServiceFieldSelectorDuration(BaseModel, extra='forbid'):
  enable_day: Optional[bool] = None
  enable_millisecond: Optional[bool] = None

class ServiceFieldSelectorEntity(BaseModel, extra='forbid'):
  multiple: Optional[bool] = None # Submitted as List[str] if multiple
  include_entities: Optional[List[str]] = None
  exclude_entities: Optional[List[str]] = None
  filter: Optional[List[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter] = None
  reorder: Optional[bool] = None # Ignore

class ServiceFieldSelectorEntityLegacy(ServiceFieldSelectorEntity):
  integration: Optional[str] = None
  domain: Optional[List[str] | str] = None
  device_class: Optional[List[str] | str] = None

class ServiceFieldSelectorFloor(BaseModel, extra='forbid'):
  entity: Optional[List[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter] = None
  device: Optional[List[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter] = None
  multiple: Optional[bool] = None

class ServiceFieldSelectorFile(BaseModel, extra='forbid'): # not supported
  accept: str

class ServiceFieldSelectorIcon(BaseModel, extra='forbid'):
  placeholder: Optional[str] = None
  fallbackPath: Optional[str] = None

class ServiceFieldSelectorImage(BaseModel, extra='forbid'): # not supported
  original: Optional[bool] = None
  crop: Optional[CropOptions] = None

class ServiceFieldSelectorLabel(BaseModel, extra='forbid'):
  multiple: Optional[bool] = None

class ServiceFieldSelectorLanguage(BaseModel, extra='forbid'):
  languages: Optional[List[str]] = None
  native_name: Optional[bool] = None # Ignored
  no_sort: Optional[bool] = None

class ServiceFieldSelectorLocation(BaseModel, extra='forbid'):
  radius: Optional[bool] = None
  radius_readonly: Optional[bool] = None
  icon: Optional[str] = None

class ServiceFieldSelectorMedia(BaseModel, extra='forbid'): # not supported
  accept: Optional[List[str]] = None

class ServiceFieldSelectorNavigation(BaseModel, extra='forbid'): # not supported
  pass

class ServiceFieldSelectorNumber(BaseModel, extra='forbid'):
  min: Optional[number] = None
  max: Optional[number] = None
  step: Optional[number | str] = None
  unit_of_measurement: Optional[str] = None
  mode: Optional[ServiceFieldSelectorNumberMode] = None
  slider_ticks: Optional[bool] = None
  translation_key: Optional[str] = None

class ServiceFieldSelectorObjectField(BaseModel, extra='forbid'):
  selector: ServiceFieldSelector
  label: Optional[str] = None
  required: Optional[bool] = None

class ServiceFieldSelectorObject(BaseModel, extra='forbid'):
  label_field: Optional[str] = None
  description_field: Optional[str] = None
  translation_key: Optional[str] = None
  fields: Dict[str, ServiceFieldSelectorObjectField] = None
  multiple: Optional[bool] = None

class ServiceFieldSelectorQRCode(BaseModel, extra='forbid'): # not supported (does not return anything)
  data: str
  scale: Optional[number] = None
  error_correction_level: Optional[ServiceFieldSelectorQRCodeErrorCorrectionLevel] = None
  center_image: Optional[str] = None

class ServiceFieldSelectorSelectOption(BaseModel, extra='forbid'):
  label: str
  value: Any
  description: Optional[str] = None
  image: Optional[str | SelectBoxOptionImage] = None
  disable: Optional[bool] = None

class ServiceFieldSelectorSelect(BaseModel, extra='forbid'):
  multiple: Optional[bool] = None # Submitted as List[str] if multiple
  custom_value: Optional[bool] = None
  mode: Optional[ServiceFieldSelectorSelectMode] = None
  options: List[str | ServiceFieldSelectorSelectOption] = None
  translation_key: Optional[str] = None
  sort: Optional[bool] = None
  reorder: Optional[bool] = None
  box_max_columns: Optional[int] = None

class ServiceFieldSelectorSelector(BaseModel, extra='forbid'): # not supported
  pass

class ServiceFieldSelectorStateOption(BaseModel, extra='forbid'):
  label: str
  value: Any

class ServiceFieldSelectorState(BaseModel, extra='forbid'): # not supported
  extra_options: Optional[List[ServiceFieldSelectorStateOption]]
  entity_id: Optional[str | List[str]]
  attribute: Optional[str] = None
  hide_states: Optional[List[str]] = None
  multiple: Optional[bool] = None

class ServiceFieldSelectorStatistic(BaseModel, extra='forbid'): # not supported (unable to fetch entities with long term stats)
  device_class: Optional[str] = None
  multiple: Optional[bool] = None

class ServiceFieldSelectorTarget(BaseModel, extra='forbid'):
  entity: Optional[List[ServiceFieldSelectorEntityFilter] | ServiceFieldSelectorEntityFilter] = None
  device: Optional[List[ServiceFieldSelectorDeviceFilter] | ServiceFieldSelectorDeviceFilter] = None

class ServiceFieldSelectorTemplate(BaseModel, extra='forbid'):
  pass

class ServiceFieldSelectorSTT(BaseModel, extra='forbid'): # not supported
  language: Optional[str] = None

class ServiceFieldSelectorText(BaseModel, extra='forbid'):
  multiline: Optional[bool] = None
  type: Optional[ServiceFieldSelectorTextType] = None
  prefix: Optional[str] = None
  suffix: Optional[str] = None
  autocomplete: Optional[str] = None
  multiple: Optional[bool] = None # Submitted as List[str] if multiple

class ServiceFieldSelectorTheme(BaseModel, extra='forbid'): # not supported
  include_default: Optional[bool] = None

class ServiceFieldSelectorTime(BaseModel, extra='forbid'):
  no_second: Optional[bool] = None

class ServiceFieldSelectorTrigger(BaseModel, extra='forbid'): # not supported
  pass

class ServiceFieldSelectorTTS(BaseModel, extra='forbid'): # not supported
  language: Optional[str] = None

class ServiceFieldSelectorTTSVoice(BaseModel, extra='forbid'): # not supported
  engineId: Optional[str] = None
  language: Optional[str] = None

class ServiceFieldSelectorUIAction(BaseModel, extra='forbid'): # not supported
  pass # Missing

class ServiceFieldSelectorUIColor(BaseModel, extra='forbid'): # not supported
  default_color: Optional[str] = None
  include_none: Optional[bool] = None
  include_state: Optional[bool] = None

class ServiceFieldSelectorUIStateContext(BaseModel, extra='forbid'): # not supported
  entity_id: Optional[str] = None
  allow_name: Optional[bool] = None

class ServiceFieldSelector(BaseModel, extra='forbid'):
  action: Optional[ServiceFieldSelectorAction] = None
  addon: Optional[ServiceFieldSelectorAddon] = None
  area: Optional[ServiceFieldSelectorArea] = None
  areas_display: Optional[ServiceFieldSelectorAreasDisplay] = None
  attribute: Optional[ServiceFieldSelectorAttribute] = None
  assist_pipeline: Optional[ServiceFieldSelectorAssistPipeline] = None
  backup_location: Optional[ServiceFieldSelectorBackupLocation] = None
  background: Optional[ServiceFieldSelectorBackground] = None
  boolean: Optional[ServiceFieldSelectorBoolean] = None
  button_toggle: Optional[ServiceFieldSelectorButtonToggle] = None
  color_rgb: Optional[ServiceFieldSelectorColorRGB] = None
  color_temp: Optional[ServiceFieldSelectorColorTemp] = None
  condition: Optional[ServiceFieldSelectorCondition] = None
  config_entry: Optional[ServiceFieldSelectorConfigEntry] = None
  constant: Optional[ServiceFieldSelectorConstant] = None
  conversation_agent: Optional[ServiceFieldSelectorConversationAgent] = None
  country: Optional[ServiceFieldSelectorCountry] = None
  date: Optional[ServiceFieldSelectorDate] = None
  datetime: Optional[ServiceFieldSelectorDateTime] = None
  device: Optional[ServiceFieldSelectorDevice | ServiceFieldSelectorDeviceLegacy] = None
  duration: Optional[ServiceFieldSelectorDuration] = None
  entity: Optional[ServiceFieldSelectorEntity | ServiceFieldSelectorEntityLegacy] = None
  floor: Optional[ServiceFieldSelectorFloor] = None
  file: Optional[ServiceFieldSelectorFile] = None
  icon: Optional[ServiceFieldSelectorIcon] = None
  image: Optional[ServiceFieldSelectorImage] = None
  label: Optional[ServiceFieldSelectorLabel] = None
  language: Optional[ServiceFieldSelectorLanguage] = None
  location: Optional[ServiceFieldSelectorLocation] = None
  media: Optional[ServiceFieldSelectorMedia] = None
  navigation: Optional[ServiceFieldSelectorNavigation] = None
  number: Optional[ServiceFieldSelectorNumber] = None
  object: Optional[ServiceFieldSelectorObject] = None
  qr_code: Optional[ServiceFieldSelectorQRCode] = None
  select: Optional[ServiceFieldSelectorSelect] = None
  selector: Optional[ServiceFieldSelectorSelector] = None
  state: Optional[ServiceFieldSelectorState] = None
  statistic: Optional[ServiceFieldSelectorStatistic] = None
  target: Optional[ServiceFieldSelectorTarget] = None
  template: Optional[ServiceFieldSelectorTemplate] = None
  stt: Optional[ServiceFieldSelectorSTT] = None
  text: Optional[ServiceFieldSelectorText] = None
  theme: Optional[ServiceFieldSelectorTheme] = None
  time: Optional[ServiceFieldSelectorTime] = None
  trigger: Optional[ServiceFieldSelectorTrigger] = None
  tts: Optional[ServiceFieldSelectorTTS] = None
  tts_voice: Optional[ServiceFieldSelectorTTSVoice] = None
  ui_action: Optional[ServiceFieldSelectorUIAction] = None
  ui_color: Optional[ServiceFieldSelectorUIColor] = None
  ui_state_content: Optional[ServiceFieldSelectorUIStateContext] = None

# Legacy replacers
def replaceLegacyEntitySelector(selector: ServiceFieldSelectorEntityLegacy | ServiceFieldSelectorEntity):
  if not isinstance(selector, ServiceFieldSelectorEntityLegacy):
    return selector # already good

  new_filter = selector.filter
  if (selector.domain is not None or selector.integration is not None or selector.device_class is not None):
    if new_filter is None:
      new_filter = []
    elif not isinstance(new_filter, list):
      new_filter = [new_filter]
    
    new_filter.append(ServiceFieldSelectorEntityFilter.model_validate({
      'domain': selector.domain,
      'integration': selector.integration,
      'device_class': selector.device_class
    }))
      
  return ServiceFieldSelectorEntity.model_validate({
    'multiple': selector.multiple,
    'include_entities': selector.include_entities,
    'exclude_entities': selector.exclude_entities,
    'filter': new_filter,
    'reorder': selector.reorder
  })

def replaceLegacyDeviceSelector(selector: ServiceFieldSelectorDeviceLegacy | ServiceFieldSelectorDevice):
  if not isinstance(selector, ServiceFieldSelectorDeviceLegacy):
    return selector # already good
  
  new_filter = selector.filter
  if (selector.integration is not None or selector.manufacturer is not None or selector.model is not None):
    if new_filter is None:
      new_filter = []
    elif not isinstance(new_filter, list):
      new_filter = [new_filter]
    
    new_filter.append(ServiceFieldSelectorDeviceFilter.model_validate({
      'integration': selector.integration,
      'manufacturer': selector.manufacturer,
      'model': selector.model
    }))
  
  return ServiceFieldSelectorDevice.model_validate({
    'entity': selector.entity,
    'filter': new_filter,
    'multiple': selector.multiple
  })

def replacePlainSelectorOptions(options: List[str | ServiceFieldSelectorSelectOption]) -> List[ServiceFieldSelectorSelectOption]:
  new_options: List[ServiceFieldSelectorSelectOption] = []

  for option in options:
    if isinstance(option, str):
      new_options.append(ServiceFieldSelectorSelectOption.model_validate({
        'label': option,
        'value': option
      }))
    elif isinstance(option, ServiceFieldSelectorSelectOption):
      new_options.append(option)

  return new_options

# Service bases

class ServiceFieldFilter(BaseModel, extra='forbid'):
  supported_features: Optional[List[int] | int] = None # Bitset (any needs to be supported [or all within specified list])
  attribute: Optional[Dict[str, List[str] | str]] = None # The field will be shown if at least one selected entity's attribute is set to one of the listed attribute states. If the attribute state is a list, the field will be shown if at least one item in a selected entity's attribute state is set to one of the listed attribute states.

class ServiceField(BaseModel, extra='forbid'):
  description: Optional[str] = None
  example: Optional[str | number | bool | List[str] | Dict] = None # Or object (recorder.get_statistics)
  default: Optional[str | number | bool | List[str] | Dict] = None
  name: Optional[str] = None
  required: Optional[bool] = None
  advanced: Optional[bool] = None
  selector: Optional[ServiceFieldSelector] = None # Field is not displayed if it's missing (only available in YAML mode)
  filter: Optional[ServiceFieldFilter] = None # Unable to utilize this information as the arguments are pre-created within slash-commands

class ServiceFieldCollection(BaseModel, extra='forbid'):
  collapsed: Optional[bool] = None
  fields: Dict[str, ServiceField]
  # Should they be sent in different format?
  
class ServiceResponse(BaseModel, extra='forbid'):
  optional: Optional[bool] = None

class ServiceModel(BaseModel, extra='forbid'):
  name: str
  description: Optional[str] = None
  fields: Optional[Dict[str, ServiceField | ServiceFieldCollection]] = None
  target: Optional[ServiceFieldSelectorTarget] = None # `area_id`, `floor_id`, `device_id``, `entity_id`, `label_id` can be passed as a target
  response: Optional[ServiceResponse] = None

class DomainModel(BaseModel, extra='forbid'):
  domain: str
  services: Dict[str, ServiceModel]
