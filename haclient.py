from homeassistant_api import Client as HAClient
from pydantic import TypeAdapter
from models.DeviceModel import DeviceModel
from typing import List, Optional

class CustomHAClient(HAClient):
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