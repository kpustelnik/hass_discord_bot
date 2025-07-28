from homeassistant_api import Client as HAClient, Group
from cachetools import TTLCache
from pydantic import TypeAdapter
from typing import List, Optional, TypeVar, Callable, Dict

from models.DeviceModel import DeviceModel
from models.ConversationModel import ConversationModel

T = TypeVar('T')

from enums.homeassistant_cache_id import homeassistant_cache_id

class CustomHAClient(HAClient):
  def __init__(self, *args, **kwargs):
    self.cache = TTLCache(maxsize=100, ttl=15*60)
    super().__init__(*args, **kwargs)
  
  def cache_data(self, func: Callable[[], T], id: str) -> T:
    data = self.cache.get(id)
    if data is None: # Need to fetch
      fetched_data = func()
      if fetched_data is not None:
        self.cache[id] = fetched_data
        data = fetched_data
    return data

  # Devices
  def custom_get_devices(self) -> List[DeviceModel]:
    fetched_devices_json = self.get_rendered_template('''
    {% set devices = states | map(attribute='entity_id') | map('device_id') | unique | reject('eq',None) | list %}
    {%- set ns = namespace(devices = []) %}
    {%- for device_id in devices %}
      {%- set entities = device_entities(device_id) | list %}
      {%- if entities %}
        {%- set ns.devices = ns.devices + [ { "id": device_id, "name": device_attr(device_id, "name"), "entities": entities } ] %}
      {%- endif %}
    {%- endfor %}
    {{ ns.devices | tojson }}
    ''')

    return TypeAdapter(List[DeviceModel]).validate_json(fetched_devices_json)
  
  def cache_custom_get_devices(self) -> List[DeviceModel]:
    return self.cache_data(lambda: self.custom_get_devices(), homeassistant_cache_id.DEVICES)

  def custom_get_device(self, device_id: str) -> Optional[DeviceModel]:
    fetched_device_json = self.get_rendered_template(
    f"{"{%"}- set device_id = '{device_id}' {"%}"}"     
    +
    '''
    {%- set entities = device_entities(device_id) | list %}
    {%- if entities %}
      {{ {
        "id": device_id,
        "name": device_attr(device_id, "name"),
        "entities": entities
      } | tojson }}
    {%- endif %}
    ''')

    if fetched_device_json == '':
      return None

    return TypeAdapter(DeviceModel).validate_json(fetched_device_json)
  
  # Entities
  def cache_get_entities(self) -> Dict[str, Group]:
    return self.cache_data(lambda: self.get_entities(), homeassistant_cache_id.ENTITIES)
  # Conversations
  def custom_conversation(self, data) -> ConversationModel:
    return ConversationModel.model_validate(self.request(
      "conversation/process",
      method="POST",
      json=data
    ))