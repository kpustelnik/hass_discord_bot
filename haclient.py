from homeassistant_api import Client as HAClient
from cachetools import TTLCache
from pydantic import TypeAdapter
from typing import List, Optional, TypeVar, Callable, Any, Tuple
from helpers import find
import re
import json
import requests

from models.DeviceModel import DeviceModel
from models.ConversationModel import ConversationModel
from models.ServiceModel import DomainModel
from models.FloorModel import FloorModel
from models.AreaModel import AreaModel
from models.EntityModel import EntityModel
from models.LabelModel import LabelModel
from models.MDIIconMeta import MDIIconMeta

T = TypeVar('T')

from enums.HomeAssistantCacheId import HomeAssistantCacheId

class CustomHAClient(HAClient):
  def __init__(self, *args, **kwargs):
    self.cache = TTLCache(maxsize=100, ttl=15*60)
    super().__init__(*args, **kwargs)
  
  @staticmethod
  def get_entity_friendlyname(entity: EntityModel) -> str | None:
    return entity.attributes["friendly_name"] if "friendly_name" in entity.attributes else None

  @staticmethod
  def escape_id(id: str) -> str:
    return re.sub('[^a-zA-Z0-9_:.]', '', id)

  def cache_data(self, func: Callable[[], T], id: str, bypass: bool = False) -> T:
    data: T | None = self.cache.get(id)
    if bypass or data is None: # Need to fetch
      fetched_data: T = func()
      if fetched_data is not None:
        self.cache[id] = fetched_data
        data = fetched_data
    if data is not None:
      return data.copy()
    return None

  # Floors
  def custom_get_floors(self) -> List[FloorModel]:
    fetched_floors_json: str = self.get_rendered_template('''
    {%- set ns = namespace(floors = []) %}
    {%- for floor_id in floors() %}
      {%- set areas = floor_areas(floor_id) | list %}
      {%- set entities = floor_entities(floor_id) | list %}
      {%- set ns.floors = ns.floors + [
        {
          "id": floor_id,
          "name": floor_name(floor_id),
          "areas": areas,
          "entities": entities
        }
      ] %}
    {%- endfor %}
    {{ ns.floors | tojson }}
    ''')

    return TypeAdapter(List[FloorModel]).validate_json(fetched_floors_json)
  
  def cache_custom_get_floors(self, bypass: bool = False) -> List[FloorModel]:
    return self.cache_data(lambda: self.custom_get_floors(), HomeAssistantCacheId.FLOORS, bypass=bypass)
  
  def custom_get_floor(self, floor_id: str) -> Optional[FloorModel]:
    fetched_floor_json: str = self.get_rendered_template(
    f"{"{%"}- set floor_id = '{self.escape_id(floor_id)}' {"%}"}"     
    +
    '''
    {%- set areas = floor_areas(floor_id) | list %}
    {%- set entities = floor_entities(floor_id) | list %}
    {%- set name = floor_name(floor_id) %}
    {%- if name %}
      {{ {
        "id": floor_id,
        "name": name,
        "areas": areas,
        "entities": entities
      } | tojson }}
    {%- endif %}
    ''')

    if fetched_floor_json == '':
      return None

    return TypeAdapter(FloorModel).validate_json(fetched_floor_json)
  
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
  
  def cache_custom_get_areas(self, bypass: bool = False) -> List[AreaModel]:
    return self.cache_data(lambda: self.custom_get_areas(), HomeAssistantCacheId.AREAS, bypass=bypass)

  def custom_get_area(self, area_id: str) -> Optional[AreaModel]:
    fetched_area_json: str = self.get_rendered_template(
    f"{"{%"}- set area_id = '{self.escape_id(area_id)}' {"%}"}"     
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
  
  # Integrations
  def custom_get_integration_entities(self, integration: str) -> List[str]:
    return json.loads(self.get_rendered_template(
      f"{"{%"}- set integration = '{self.escape_id(integration)}' {"%}"}"     
      +
      '''
        {{ integration_entities(integration) | tojson }}                     
      '''
    ))

  # Labels
  def custom_get_labels(self) -> List[LabelModel]:
    fetched_labels_json: str = self.get_rendered_template('''
    {%- set ns = namespace(labels = []) %}
    {%- for label_id in labels() %}
      {%- set areas = label_areas(label_id) | list %}
      {%- set devices = label_devices(label_id) | list %}
      {%- set entities = label_entities(label_id) | list %}
      {%- set ns.labels = ns.labels + [
        {
          "id": label_id,
          "name": label_name(label_id),
          "description": label_description(label_id),
          "areas": areas,
          "devices": devices,
          "entities": entities
        }
      ] %}
    {%- endfor %}
    {{ ns.labels | tojson }}
    ''')

    return TypeAdapter(List[LabelModel]).validate_json(fetched_labels_json)
  
  def cache_custom_get_labels(self, bypass: bool = False) -> List[LabelModel]:
    return self.cache_data(lambda: self.custom_get_labels(), HomeAssistantCacheId.LABELS, bypass=bypass)

  def custom_get_label(self, label_id: str) -> Optional[LabelModel]:
    fetched_label_json: str = self.get_rendered_template(
    f"{"{%"}- set label_id = '{self.escape_id(label_id)}' {"%}"}"     
    +
    '''
    {%- set areas = label_areas(label_id) | list %}
    {%- set devices = label_devices(label_id) | list %}
    {%- set entities = label_entities(label_id) | list %}
    {{ {
      "id": label_id,
      "name": label_name(label_id),
      "description": label_description(label_id),
      "areas": areas,
      "devices": devices,
      "entities": entities
    } | tojson }}
    ''')

    if fetched_label_json == '':
      return None

    return TypeAdapter(LabelModel).validate_json(fetched_label_json)
  
  # Devices
  def custom_get_devices(self) -> List[DeviceModel]:
    fetched_devices_json: str = self.get_rendered_template('''
    {% set devices = states | map(attribute='entity_id') | map('device_id') | unique | reject('eq',None) | list %}
    {%- set ns = namespace(devices = []) %}
    {%- for device_id in devices %}
      {%- set entities = device_entities(device_id) | list %}
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
    {%- endfor %}
    {{ ns.devices | tojson }}
    ''')

    return TypeAdapter(List[DeviceModel]).validate_json(fetched_devices_json)
  
  def cache_custom_get_devices(self, bypass: bool = False) -> List[DeviceModel]:
    return self.cache_data(lambda: self.custom_get_devices(), HomeAssistantCacheId.DEVICES, bypass=bypass)

  def custom_get_device(self, device_id: str) -> Optional[DeviceModel]:
    fetched_device_json: str = self.get_rendered_template(
    f"{"{%"}- set device_id = '{self.escape_id(device_id)}' {"%}"}"     
    +
    '''
    {%- set entities = device_entities(device_id) | list %}
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
    ''')

    if fetched_device_json == '':
      return None

    return TypeAdapter(DeviceModel).validate_json(fetched_device_json)
  
  # Entities
  def custom_get_entities(self) -> List[EntityModel]:
    return TypeAdapter(List[EntityModel]).validate_python(self.request("states"))

  def cache_custom_get_entities(self, bypass: bool = False) -> List[EntityModel]:
    return self.cache_data(lambda: self.custom_get_entities(), HomeAssistantCacheId.ENTITIES, bypass=bypass)
  
  def custom_get_entity(self, entity_id: str) -> Optional[EntityModel]:
    return EntityModel.model_validate(self.request(f"states/{self.escape_id(entity_id)}"))
  
  # Services
  def custom_get_domains(self) -> List[DomainModel]:
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
        fields_tofix_queue = []
        if service_fields is not None:
          fields_tofix_queue.append(service_fields)
        
        # Loop for fixing the service fields (proper parsing of [type]: null)
        while len(fields_tofix_queue) > 0:
          fields = fields_tofix_queue.pop(0)
          for field in fields.values():
            field_selector = field.get('selector', None)
            if field_selector is not None:
              for i, v in field_selector.items():
                if v is None:
                  field_selector[i] = {} # Create empty object

            field_fields = field.get('fields', None)
            if field_fields is not None:
              fields_tofix_queue.append(field_fields)
    
    return TypeAdapter(List[DomainModel]).validate_python(fetched_domains)

  def cache_custom_get_domains(self, bypass: bool = False) -> List[DomainModel]:
    return self.cache_data(lambda: self.custom_get_domains(), HomeAssistantCacheId.DOMAINS, bypass=bypass)
  
  def custom_get_domain(self, domain_name: str) -> Optional[DomainModel]:
    domains = self.custom_get_domains()
    return find(lambda x: x.name == domain_name, domains)

  # Conversations
  def custom_conversation(self, data) -> ConversationModel:
    return ConversationModel.model_validate(self.request(
      "conversation/process",
      method="POST",
      json=data
    ))
  
  # Triggering services
  def custom_trigger_services(self, domain: str, service: str, **service_data) -> List[EntityModel]:
    data = self.request(
      f"services/{self.escape_id(domain)}/{self.escape_id(service)}",
      method="POST",
      json=service_data
    )
    return TypeAdapter(List[EntityModel]).validate_python(data)

  def custom_trigger_service_with_response(self, domain: str, service: str, **service_data) -> Tuple[List[EntityModel], dict[str, Any]]:
    data = self.request(
      f"services/{self.escape_id(domain)}/{self.escape_id(service)}?return_response",
      method='POST',
      json=service_data
    )

    return (
      TypeAdapter(List[EntityModel]).validate_python(data.get('changed_states', [])),
      data.get("service_response", {})
    )
  
  # Templating
  def format_string(self, txt: str) -> str:
    homeassistant_entities: List[EntityModel] = self.custom_get_entities()
    if homeassistant_entities is None:
      raise Exception("No entities were returned")

    def replacer(match):
        entity_id = match.group(1)
        entity = find(lambda entity: entity.entity_id == entity_id, homeassistant_entities)
        if entity is not None:
          return entity.state
        else:
          return ''
    
    return re.sub(r'\{([^\}]+)\}', replacer, txt)
  
  # MDI Icons
  def get_mdi_icons(self) -> List[MDIIconMeta]:
    result = requests.get('https://raw.githubusercontent.com/Templarian/MaterialDesign-SVG/master/meta.json')
    return TypeAdapter(List[MDIIconMeta]).validate_python(result.json())
  
  def cache_get_mdi_icons(self, bypass: bool = False) -> List[MDIIconMeta]:
    return self.cache_data(lambda: self.get_mdi_icons(), 'MDI_ICONS', bypass=bypass)