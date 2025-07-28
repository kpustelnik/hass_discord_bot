from homeassistant_api import Client as HAClient, Group
from cachetools import TTLCache
from pydantic import TypeAdapter
from typing import List, Optional, TypeVar, Callable, Dict

from models.DeviceModel import DeviceModel
from models.ConversationModel import ConversationModel
from models.ServiceModel import DomainModel
from models.AreaModel import AreaModel

T = TypeVar('T')

from enums.HomeAssistantCacheId import HomeAssistantCacheId

class CustomHAClient(HAClient):
  def __init__(self, *args, **kwargs):
    self.cache = TTLCache(maxsize=100, ttl=15*60)
    super().__init__(*args, **kwargs)
  
  def cache_data(self, func: Callable[[], T], id: str) -> T:
    data: T | None = self.cache.get(id)
    if data is None: # Need to fetch
      fetched_data: T = func()
      if fetched_data is not None:
        self.cache[id] = fetched_data
        data = fetched_data
    return data
  
  # Areas
  def custom_get_areas(self) -> List[AreaModel]:
    fetched_areas_json: str = self.get_rendered_template('''
    {%- set ns = namespace(areas = []) %}
    {%- for area_id in areas() %}
      {%- set entities = area_entities(area_id) | list %}
      {%- set devices = area_devices(area_id) | list %}
      {%- set ns.areas = ns.areas + [
        {
          "id": area_id,
          "name": area_name(area_id),
          "entities": entities,
          "devices": devices
        }
      ] %}
    {%- endfor %}
    {{ ns.areas | tojson }}
    ''')

    return TypeAdapter(List[AreaModel]).validate_json(fetched_areas_json)
  
  def cache_custom_get_areas(self) -> List[AreaModel]:
     return self.cache_data(lambda: self.custom_get_areas(), HomeAssistantCacheId.AREAS)

  def custom_get_area(self, area_id: str) -> Optional[AreaModel]:
    # TODO: Escape the area_id
    fetched_area_json: str = self.get_rendered_template(
    f"{"{%"}- set area_id = '{area_id}' {"%}"}"     
    +
    '''
    {%- set entities = area_entities(area_id) | list %}
    {%- set devices = area_devices(area_id) | list %}
    {%- set name = area_name(area_id) %}
    {%- if name %}
      {{ {
        "id": area_id,
        "name": name,
        "entities": entities,
        "devices": devices
      } | tojson }}
    {%- endif %}
    ''')

    if fetched_area_json == '':
      return None

    return TypeAdapter(AreaModel).validate_json(fetched_area_json)

  # Devices
  def custom_get_devices(self) -> List[DeviceModel]:
    fetched_devices_json: str = self.get_rendered_template('''
    {% set devices = states | map(attribute='entity_id') | map('device_id') | unique | reject('eq',None) | list %}
    {%- set ns = namespace(devices = []) %}
    {%- for device_id in devices %}
      {%- set entities = device_entities(device_id) | list %}
      {%- if entities %}
        {%- set ns.devices = ns.devices + [
          {
            "id": device_id,
            "area_id": device_attr(device_id, "area_id"),
            "device_id": device_attr(device_id, "device_id"),
            "name": device_attr(device_id, "name"),
            "name_by_user": device_attr(device_id, "name_by_user"),
            "manufacturer": device_attr(device_id, "manufacturer"),
            "model": device_attr(device_id, "model"),
            "model_id": device_attr(device_id, "model_id"),
            "serial_number": device_attr(device_id, "serial_number"),
            "hw_version": device_attr(device_id, "hw_version"),
            "sw_version": device_attr(device_id, "sw_version"),
            "entities": entities
          }
        ] %}
      {%- endif %}
    {%- endfor %}
    {{ ns.devices | tojson }}
    ''')

    return TypeAdapter(List[DeviceModel]).validate_json(fetched_devices_json)
  
  def cache_custom_get_devices(self) -> List[DeviceModel]:
    return self.cache_data(lambda: self.custom_get_devices(), HomeAssistantCacheId.DEVICES)

  def custom_get_device(self, device_id: str) -> Optional[DeviceModel]:
    # TODO: Escape the device id
    fetched_device_json: str = self.get_rendered_template(
    f"{"{%"}- set device_id = '{device_id}' {"%}"}"     
    +
    '''
    {%- set entities = device_entities(device_id) | list %}
    {%- if entities %}
      {{ {
        "id": device_id,
        "area_id": device_attr(device_id, "area_id"),
        "device_id": device_attr(device_id, "device_id"),
        "name": device_attr(device_id, "name"),
        "name_by_user": device_attr(device_id, "name_by_user"),
        "manufacturer": device_attr(device_id, "manufacturer"),
        "model": device_attr(device_id, "model"),
        "model_id": device_attr(device_id, "model_id"),
        "serial_number": device_attr(device_id, "serial_number"),
        "hw_version": device_attr(device_id, "hw_version"),
        "sw_version": device_attr(device_id, "sw_version"),
        "entities": entities
      } | tojson }}
    {%- endif %}
    ''')

    if fetched_device_json == '':
      return None

    return TypeAdapter(DeviceModel).validate_json(fetched_device_json)
  
  # Entities
  def cache_get_entities(self) -> Dict[str, Group]:
    return self.cache_data(lambda: self.get_entities(), HomeAssistantCacheId.ENTITIES)
  
  # Services
  def custom_get_domains(self) -> List[DomainModel]:
    # Function for fixing the service fields (proper parsing of [type]: null)
    def fix_service_fields(fields):
      for field in fields.values():
        field_selector = field.get('selector', None)
        if field_selector is not None:
          for i, v in field_selector.items():
            if v is None:
              field_selector[i] = {} # Create empty object

        field_fields = field.get('fields', None)
        if field_fields is not None:
          fix_service_fields(field_fields)

    # Apply fixes to all services
    fetched_domains = self.request("services")
    for domain in fetched_domains:
      for service in domain["services"].values():
        # Fix targets (get rid of the list)
        service_target = service.get("target", None)
        if service_target is not None:
          service_target_entity = service_target.get("entity", None)
          if service_target_entity is not None:
            service_target["entity"] = service_target_entity[0]

          service_target_device = service_target.get("device", None)
          if service_target_device is not None:
            service_target["device"] = service_target_device[0]
        
        # Fix field selectors
        service_fields = service.get("fields", None)
        if service_fields is not None:
          fix_service_fields(service_fields)
    
    return TypeAdapter(List[DomainModel]).validate_python(fetched_domains)

  def cache_custom_get_domains(self) -> List[DomainModel]:
    return self.cache_data(lambda: self.custom_get_domains(), HomeAssistantCacheId.DOMAINS)

  # Conversations
  def custom_conversation(self, data) -> ConversationModel:
    return ConversationModel.model_validate(self.request(
      "conversation/process",
      method="POST",
      json=data
    ))