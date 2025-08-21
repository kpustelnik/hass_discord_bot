from typing import Optional, Literal, List, Dict, Any, Callable, Set
import discord
from discord.ext import commands
from discord import app_commands
import json
import inspect
from helpers import shorten, shorten_argument_rename, to_list, is_matching
import datetime
import re
import pycountry
import langcodes
from langcodes.language_lists import CLDR_LANGUAGES

from bot import HASSDiscordBot
from autocompletes import transform_multiple, transform_object, transform_multiple_autocomplete, multiple_autocomplete, icon_autocomplete, filtered_label_autocomplete, filtered_floor_autocomplete, filtered_area_autocomplete, filtered_device_autocomplete, filtered_entity_autocomplete, require_choice, label_floor_area_device_entity_autocomplete, choice_autocomplete, require_permission_autocomplete
from functools import partial
from enums.emojis import Emoji
from models.ServiceModel import ServiceFieldSelectorLocation, ServiceFieldSelectorDuration, DomainModel, ServiceModel, ServiceFieldSelectorDevice, ServiceFieldSelectorEntity, ServiceFieldCollection, ServiceField, ServiceFieldSelectorSelectOption, ServiceFieldSelectorEntityFilter, replacePlainSelectorOptions, replaceLegacyDeviceSelector, replaceLegacyEntitySelector
from homeassistant_api.errors import RequestError

ALL_LANGUAGES: List[langcodes.Language] = [langcodes.get(x) for x in CLDR_LANGUAGES]

def transform_duration(input: str, selector: ServiceFieldSelectorDuration):
  split = [int(x) for x in input.split(':')]
  expected_count = 3 + int(selector.enable_day == True) + int(selector.enable_millisecond == True)
  if len(split) != expected_count:
    raise Exception("Incorrect duration format.")
  
  obj: Dict[str, int] = dict()
  offset = 1 if selector.enable_day == True else 0

  if selector.enable_day == True:
    days = split[0]
    if days < 0: raise Exception("Days must be lower or equal to 0")
    obj['days'] = days
  
  hours = split[offset]
  if hours < 0 or hours >= 24: raise Exception("Hours must be between 0 and 23")
  obj['hours'] = hours

  mins = split[offset + 1]
  if mins < 0 or mins >= 60: raise Exception("Minutes must be between 0 and 59")
  obj['minutes'] = mins

  seconds = split[offset + 2]
  if seconds < 0 or seconds >= 60: raise Exception("Seconds must be between 0 and 59")
  obj['seconds'] = seconds

  if selector.enable_millisecond == True:
    milliseconds = split[offset + 3]
    if milliseconds < 0 or milliseconds >= 60: raise Exception("Milliseconds must be between 0 and 60")
    obj['milliseconds'] = milliseconds
  
  return obj

def transform_location(input: str, selector: ServiceFieldSelectorLocation, default_radius: float=None):
  split = [float(x) for x in input.split(';')]
  expected_count = 2 + int(selector.radius == True and not (selector.radius_readonly == True))
  if len(split) != expected_count:
    raise Exception("Incorrect location format.")

  obj: Dict[str, int] = dict()
  
  lat: float = split[0]
  if lat < -90 or lat > 90: raise Exception("Latitude must be between -90 and 90")
  obj['latitude'] = lat

  lon: float = split[1]
  if lat < -180 or lat > 180: raise Exception("Longitude must be between -180 and 180")
  obj['longitude'] = lon

  if selector.radius == True:
    if selector.radius_readonly == True:
      if default_radius is None:
        raise Exception("No preset radius")
      obj['radius'] = default_radius
    else:
      obj['radius'] = split[2]
  
  return obj

class Services(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    self.WHITELISTED_SERVICES = [
      ['light', 'turn.*']
    ]
    self.USE_AUTOCOMPLETE_MULTIPLE = True
    self.ALLOW_UNSUPPORTED = True

  async def cog_load(self) -> None:
    try:
      ha_domains: List[DomainModel] = await self.bot.homeassistant_client.cache_async_custom_get_domains()
      for domain in ha_domains:
        group = app_commands.Group(
          name=domain.domain,
          description=f"{domain.domain} services (actions)",
          allowed_contexts=app_commands.AppCommandContext(guild=True, dm_channel=True, private_channel=True),
          allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
        )

        any_added = False
        for service_id, service in domain.services.items():
          if self.check_whitelist(domain.domain, service_id):
            any_added = True
            await self.create_service_command(group, domain, service_id, service)

        if any_added:
          self.bot.tree.add_command(group)
    except Exception as e:
      self.bot.logger.error("Failed to fetch domains and create service action commands - %s %s", type(e), e)

  def check_whitelist(self, domain_id, service_id) -> bool:
    for tmpl_domain_id, tmpl_service_id in self.WHITELISTED_SERVICES:
      if re.match(tmpl_domain_id, domain_id) is not None and re.match(tmpl_service_id, service_id) is not None:
        return True
    return False
  
  @staticmethod
  def parse_targets(targets: List[str]) -> Dict:
    parsed_kwargs = {}
    area_ids: List[str] = []
    device_ids: List[str] = []
    entity_ids: List[str] = []
    floor_ids: List[str] = []
    label_ids: List[str] = []

    for subtarget in targets:
      match subtarget:
        case s if s.startswith('AREA$'):
          area_ids.append(s[len('AREA$'):])
        case s if s.startswith('DEVICE$'):
          device_ids.append(s[len('DEVICE$'):])
        case s if s.startswith('ENTITY$'):
          entity_ids.append(s[len('ENTITY$'):])
        case s if s.startswith('FLOOR$'):
          floor_ids.append(s[len('FLOOR$'):])
        case s if s.startswith('LABEL$'):
          label_ids.append(s[len('LABEL$'):])
    
    if len(area_ids) > 0: parsed_kwargs['area_id'] = area_ids
    if len(device_ids) > 0: parsed_kwargs['device_id'] = device_ids
    if len(entity_ids) > 0: parsed_kwargs['entity_id'] = entity_ids
    if len(floor_ids) > 0: parsed_kwargs['floor_id'] = floor_ids
    if len(label_ids) > 0: parsed_kwargs['label_id'] = label_ids
    
    return parsed_kwargs
  
  async def create_service_command(self, group: app_commands.Group, domain: DomainModel, service_id: str, service: ServiceModel) -> None:
    # Create handler function
    constants: Dict[str, Any] = {}
    transformers: Dict[str, Callable[[Any, discord.Interaction], Any]] = {}
    renames: Dict[str, str] = {}
    async def handler(interaction: discord.Interaction, **kwargs):
      if not await self.bot.check_user_guild(interaction, check_role=True):
        return
    
      await interaction.response.defer(thinking=True)

      # Apply the argument constants
      for id, value in constants.items():
        if kwargs[id] == True:
          kwargs[id] = value
        else:
          del kwargs[id]

      # Apply argument transformers
      try:
        final_kwargs = {
          name: transformers[name](value, interaction) if name in transformers else value
          for name, value in kwargs.items() if value is not None
        }
      except Exception as e:
        self.bot.logger.error('Failed to apply transformers - %s %s', type(e), e)
        await interaction.followup.send(f'{Emoji.ERROR} {str(e)}', ephemeral=True)
        return

      # Parse the target if available
      final_targets: List[str] | None = None
      if 'service_action_target' in final_kwargs:
        target = final_kwargs['service_action_target']
        del final_kwargs['service_action_target']
        final_targets = to_list(target)
        final_kwargs.update(self.parse_targets(final_targets))

      # Send the request
      try:
        try:
          changed_entities, response_data = await self.bot.homeassistant_client.async_custom_trigger_service_with_response(
            domain.domain,
            service_id,
            **final_kwargs
          )
        except RequestError:
          response_data = None
          changed_entities = await self.bot.homeassistant_client.async_custom_trigger_services(
            domain.domain,
            service_id,
            **final_kwargs
          )
      except Exception as e:
        self.bot.logger.error("Failed to send action to HomeAssistant - %s %s", type(e), e)
        await interaction.followup.send(f'{Emoji.ERROR} Failed to send action to HomeAssistant', ephemeral=True)
        return

      # Create embed
      embed = discord.Embed(
        title=f"{domain.domain} > {service.name} execution",
        description=f'{Emoji.SUCCESS} Service action succeeded',
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      if final_targets is not None:
        embed.add_field(
          name='Action targets',
          value='\n'.join(final_targets)
        )

      for i in ['area_id', 'device_id', 'entity_id', 'floor_id', 'label_id']: # Remove the raw target ids from final arguments
        if i in final_kwargs: del final_kwargs[i]

      for i, v in final_kwargs.items():
        if v is not None:
          id = renames[i] if i in renames else i
          embed.add_field(
            name=str(id),
            value=str(v)
          )

      if len(changed_entities) > 0:
        embed.add_field(
          name=f'Changed entities',
          value=shorten("\n".join([
            f"**{friendly_name if (friendly_name := self.bot.homeassistant_client.get_entity_friendlyname(entity)) is not None else "?"}** ({entity.entity_id})"
            for entity in changed_entities
          ]), 1024)
        )

      try:
        content = None
        if response_data is not None:
          content = f'```json\n{json.dumps(response_data, indent=2)}\n```'

        await interaction.followup.send(embed=embed, content=content)
      except Exception as e:
        self.bot.logger.error("Failed to construct the response - %s %s", type(e), e)
        await interaction.followup.send(f'{Emoji.ERROR} Failed to construct the response', ephemeral=True)
        return

    # Adjust handler function properties
    handler.__name__ = f"{service_id}"  # required to avoid duplicate names
    handler.__qualname__ = handler.__name__
    
    params: List[inspect.Parameter] = [
        inspect.Parameter(
            name="interaction",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=discord.Interaction
        )
    ]
    descriptions: Dict[str, str] = {}
    autocomplete_replacements: Dict[str, Any] = {}
    all_params: Set[str] = set()

    if service.target is not None and service.target.entity is not None:
      params.append(
        inspect.Parameter(
          name="service_action_target",
          kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
          annotation=str
        )
      )
      renames["service_action_target"] = "Service Action Target"
      descriptions["service_action_target"] = "HomeAssistant service action target"
      if self.USE_AUTOCOMPLETE_MULTIPLE:
        autocomplete_replacements["service_action_target"] = partial(
          multiple_autocomplete,
          func=partial(
            label_floor_area_device_entity_autocomplete,
            entity_filter=to_list(service.target.entity),
            device_filter=to_list(service.target.device)
          ),
          allow_custom=True
        )
        transformers["service_action_target"] = transform_multiple_autocomplete
      else:
        autocomplete_replacements["service_action_target"] = partial(
          label_floor_area_device_entity_autocomplete,
          entity_filter=to_list(service.target.entity),
          device_filter=to_list(service.target.device)
        )
        transformers["service_action_target"] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
      all_params.add('service_action_target')

    try:
      if service.fields is not None:
        fields_queue: Dict[str, ServiceFieldCollection | ServiceField] = [service.fields]

        while len(fields_queue) > 0:
          fields = fields_queue.pop(0)
          for i, (field_id, field) in enumerate(fields.items()):
              if isinstance(field, ServiceFieldCollection):
                fields_queue.append(field.fields)
                continue

              if field.selector is None: # Ignore fields that wouldn't be visible in DevTools UI Action runner
                continue

              is_hidden: bool = False
              field_type = None
              default_value = None
              additional_description: str | None = None
              if field.selector.area is not None: # ServiceFieldSelectorArea
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.area.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(
                        filtered_area_autocomplete,
                        entity_filter=to_list(field.selector.area.entity),
                        device_filter=to_list(field.selector.area.device)
                      ),
                      allow_custom=True
                    )
                    transformers[field_id] = transform_multiple_autocomplete
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
                else:
                  autocomplete_replacements[field_id] = partial(filtered_area_autocomplete, entity_filter=to_list(field.selector.area.entity), device_filter=to_list(field.selector.area.device))

              elif field.selector.attribute is not None: # ServiceFieldSelectorAttribute
                field_type = str
                if field.default is not None: default_value = str(field.default)
                homeassistant_entities = await self.bot.homeassistant_client.cache_async_custom_get_entities()
                attributes: Set[str] = set()
                if field.selector.attribute.entity_id is not None:
                  for entity in homeassistant_entities:
                    if is_matching(field.selector.attribute.entity_id, entity.entity_id):
                      for attribute, _ in entity.attributes.items():
                        if field.selector.attribute.hide_attributes is None or attribute not in field.selector.attribute.hide_attributes:
                          attributes.add(attribute)

                attribute_options = replacePlainSelectorOptions(list(attributes))
                autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=attribute_options)
                transformers[field_id] = partial(require_choice, all_choices=attribute_options)

              elif field.selector.boolean is not None: # ServiceFieldSelectorBoolean
                field_type = bool
                if field.default is not None: default_value = bool(field.default)
                
              elif field.selector.button_toggle is not None: # ServiceFieldSelectorButtonToggle
                field_all_options = field.selector.button_toggle.options
                if field.selector.button_toggle.sort == True:
                  field_all_options.sort(key=lambda x: x if isinstance(x, str) else x.label)

                are_all_strings: bool = all(isinstance(x, str) for x in field_all_options)
                field_options: List[ServiceFieldSelectorSelectOption] = replacePlainSelectorOptions(field_all_options)
                
                if field.default is not None: default_value = type(field_options[0].value)(field.default) if len(field_options) > 0 else field.default
                if len(field_all_options) > 25 or not are_all_strings: # Too many options (or they're not plain strings), use autocomplete
                  autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=field_options)
                  transformers[field_id] = partial(require_choice, all_choices=field_options)
                  field_type = str
                else:
                  field_type = Literal[*field_all_options]
                  
              elif field.selector.color_rgb is not None: # ServiceFieldSelectorColorRGB
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, int) and x >= 0 and x <= 255, minlen=3, maxlen=3, delimiter=';', delimiter_transformer=lambda x: int(x))
                additional_description = 'R;G;B'

              elif field.selector.color_temp is not None: # ServiceFieldSelectorColorTemp
                subtype = int
                min_val = field.selector.color_temp.min if field.selector.color_temp.min is not None else field.selector.color_temp.min_mireds
                max_val = field.selector.color_temp.max if field.selector.color_temp.max is not None else field.selector.color_temp.max_mireds
                if min_val is not None or max_val is not None:
                  if max_val is not None:
                    if max_val > 9007199254740991:
                      max_val = 9007199254740991
                    max_val = subtype(max_val)
                  if min_val is not None:
                    if min_val < -9007199254740991:
                      min_val = -9007199254740991
                    min_val = subtype(min_val)
                  field_type = app_commands.Range[subtype, min_val, max_val]
                else:
                  field_type = subtype
                if field.default is not None: default_value = subtype(field.default)

              elif field.selector.constant is not None: # ServiceFieldSelectorConstant
                field_type = bool
                if field.default is not None:
                  default_value = field.default
                else:
                  default_value = False

                if field.selector.constant.label is not None:
                  additional_description = field.selector.constant.label
                constants[field_id] = field.selector.constant.value
              
              elif field.selector.conversation_agent is not None: # ServiceFieldSelectorConversationAgent
                field_type = str
                if field.default is not None: default_value = str(field.default)
                autocomplete_replacements[field_id] = partial(filtered_entity_autocomplete, entity=to_list(ServiceFieldSelectorEntityFilter.model_validate({ 'domain': 'conversation' })))
              
              elif field.selector.country is not None: # ServiceFieldSelectorCountry
                field_type = str
                countries: List[pycountry.ExistingCountries] = [
                  country
                  for code in field.selector.country.countries
                  if (country := pycountry.countries.get(alpha_2=code) or pycountry.countries.get(alpha_3=code)) is not None
                ]
                if not (field.selector.country.no_sort == True):
                  countries.sort(key=lambda x: x.name)

                country_options: List[ServiceFieldSelectorSelectOption] = [
                  ServiceFieldSelectorSelectOption.model_validate({
                    'label': x.name,
                    'value': x.alpha_2 # Home Assistant uses alpha2 ISO 3166
                  })
                  for x in countries
                ]
                autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=country_options)
                transformers[field_id] = partial(require_choice, all_choices=country_options)
                if field.default is not None: default_value = str(field.default)

              elif field.selector.date is not None: # ServiceFieldSelectorDate
                field_type = str
                if field.default is not None: default_value = str(field.default)
                additional_description = 'YYYY-MM-DD'
              
              elif field.selector.datetime is not None: # ServiceFieldSelectorDateTime
                field_type = str
                if field.default is not None: default_value = str(field.default)
                additional_description = 'YYYY-MM-DD HH:MM:SS'

              elif field.selector.device is not None: # ServiceFieldSelectorDevice | ServiceFieldSelectorDeviceLegacy
                new_device_selector: ServiceFieldSelectorDevice = replaceLegacyDeviceSelector(field.selector.device)

                field_type = str
                if field.default is not None: default_value = str(field.default)
                if new_device_selector.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(
                        filtered_device_autocomplete,
                        entity_filter=to_list(new_device_selector.entity),
                        device_filter=to_list(new_device_selector.filter)
                      ),
                      allow_custom=True
                    )
                    transformers[field_id] = transform_multiple_autocomplete
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
                else:
                  autocomplete_replacements[field_id] = partial(filtered_device_autocomplete, device_filter=to_list(new_device_selector.filter), entity_filter=to_list(new_device_selector.entity))

              elif field.selector.duration is not None: # ServiceFieldSelectorDuration
                field_type = str
                if field.default is not None:
                  all_values: List[str] = []
                  if field.selector.duration.enable_days:
                    all_values.append(str(field.default.days))
                  all_values.append(str(field.default.hours))
                  all_values.append(str(field.default.minutes))
                  all_values.append(str(field.default.seconds))
                  if field.selector.duration.milliseconds:
                    all_values.append(str(field.default.milliseconds))
                  default_value = ':'.join(all_values)

                additional_description = f'{'DD:' if field.selector.duration.enable_day == True else ''}HH:MM:SS{':mm' if field.selector.duration.enable_millisecond == True else ''}'
                transformers[field_id] = partial(transform_duration, selector=field.selector.duration)

              elif field.selector.entity is not None: # ServiceFieldSelectorEntity | ServiceFieldSelectorEntityLegacy
                new_entity_selector: ServiceFieldSelectorEntity = replaceLegacyEntitySelector(field.selector.entity)
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if new_entity_selector.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(
                        filtered_entity_autocomplete,
                        entity_filter=to_list(new_entity_selector.filter),
                        exclude_values=field.selector.entity.exclude_entities,
                        include_values=field.selector.entity.include_entities
                      ),
                      allow_custom=True
                    )
                    transformers[field_id] = transform_multiple_autocomplete
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
                else:
                  autocomplete_replacements[field_id] = partial(
                    filtered_entity_autocomplete,
                    entity_filter=to_list(new_entity_selector.filter),
                    exclude_values=field.selector.entity.exclude_entities,
                    include_values=field.selector.entity.include_entities
                  )
                
              elif field.selector.floor is not None: # ServiceFieldSelectorFloor
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.floor.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(
                        filtered_floor_autocomplete,
                        entity_filter=to_list(field.selector.floor.entity),
                        device_filter=to_list(field.selector.floor.device)
                      ),
                      allow_custom=True
                    )
                    transformers[field_id] = transform_multiple_autocomplete
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
                else:
                  autocomplete_replacements[field_id] = partial(filtered_floor_autocomplete, entity_filter=to_list(field.selector.floor.entity), device_filter=to_list(field.selector.floor.device))
                
              elif field.selector.icon is not None: # ServiceFieldSelectorIcon
                field_type = str
                if field.default is not None: default_value = str(field.default)
                autocomplete_replacements[field_id] = icon_autocomplete

              elif field.selector.label is not None: # ServiceFieldSelectorLabel
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.label.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(
                        filtered_label_autocomplete,
                        entity_filter=to_list(field.selector.label.entity),
                        device_filter=to_list(field.selector.label.device)
                      ),
                      allow_custom=True
                    )
                    transformers[field_id] = transform_multiple_autocomplete
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
                else:
                  autocomplete_replacements[field_id] = partial(filtered_label_autocomplete, entity_filter=to_list(field.selector.label.entity), device_filter=to_list(field.selector.label.device))

              elif field.selector.language is not None: # ServiceFieldSelectorLanguage
                field_type = str
                languages: List[langcodes.Language] = ALL_LANGUAGES
                if field.selector.language.languages is not None:
                  languages = [
                    language
                    for code in field.selector.language.languages
                    if (language := langcodes.find(code) or langcodes.get(code)) is not None
                  ]

                if not (field.selector.language.no_sort == True):
                  languages.sort(key=lambda x: x.display_name())

                language_options: List[ServiceFieldSelectorSelectOption] = [
                  ServiceFieldSelectorSelectOption.model_validate({
                    'label': x.display_name(),
                    'value': x.to_tag()
                  })
                  for x in languages
                ]
                autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=language_options)
                transformers[field_id] = partial(require_choice, all_choices=language_options)

              elif field.selector.location is not None: # ServiceFieldSelectorLocation
                field_type = str
                if field.default is not None:
                  all_values: List[str] = []
                  all_values.append(str(field.default.latitude))
                  all_values.append(str(field.default.longitude))
                  if field.selector.location.radius:
                    all_values.append(str(field.default.radius))
                  default_value = ';'.join(all_values)

                additional_description = f'LAT;LONG{';RADIUS' if field.selector.location.radius == True else ''}'
                transformers[field_id] = partial(transform_location, selector=field.selector.location, default_radius=field.default.radius if field.default is not None else None)
                field_type = str
                
              elif field.selector.number is not None: # ServiceFieldSelectorNumber
                subtype = float if field.selector.number is not None and isinstance(field.selector.number, int) and field.selector.number.step != 1 else int
                max_val = field.selector.number.max
                min_val = field.selector.number.min
                if min_val is not None or max_val is not None:
                  if max_val is not None:
                    if max_val > 9007199254740991:
                      max_val = 9007199254740991
                    max_val = subtype(max_val)
                  if min_val is not None:
                    if min_val < -9007199254740991:
                      min_val = -9007199254740991
                    min_val = subtype(min_val)
                  field_type = app_commands.Range[subtype, min_val, max_val]
                else:
                  field_type = subtype
                if field.default is not None: default_value = subtype(field.default)
                if field.selector.number.unit_of_measurement is not None:
                  additional_description = str(field.selector.number.unit_of_measurement)

              elif field.selector.object is not None: # ServiceFieldSelectorObject
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = lambda x, _: to_list(transform_object(x)) if field.selector.object.multiple == True else transform_object(x)

              elif field.selector.select is not None: # ServiceFieldSelectorSelect
                field_all_options = field.selector.select.options
                if field.selector.select.sort == True:
                  field_all_options.sort(key=lambda x: x if isinstance(x, str) else x.label)

                are_all_strings: bool = all(isinstance(x, str) for x in field_all_options)
                field_options: List[ServiceFieldSelectorSelectOption] = replacePlainSelectorOptions(field_all_options)

                if field.selector.select.multiple == True:
                  if field.default is not None: default_value = str(field.default)
                  field_type = str
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(choice_autocomplete, all_choices=field_options),
                      allow_custom=field.selector.select.custom_value == True
                    )
                    transformers[field_id] = partial(
                      lambda c_field_options, c_allow_custom, x_in, interaction: transform_multiple_autocomplete(
                        x_in,
                        interaction,
                        default_transform_custom_checker=lambda x: (len(c_field_options) == 0 or isinstance(x, type(c_field_options[0].value))) and require_choice(x, interaction, all_choices=c_field_options, allow_custom=c_allow_custom),
                        default_transform_transformer=lambda x: type(c_field_options[0].value)(x) if len(c_field_options) > 0 else x
                      ),
                      field_options, field.selector.select.custom_value == True
                    )
                  else:
                    transformers[field_id] = partial(lambda c_field_options, c_allow_custom, input: transform_multiple(
                      input,
                      lambda x, _: (len(c_field_options) == 0 or isinstance(x, type(c_field_options[0].value))) and require_choice(x, all_choices=c_field_options, allow_custom=c_allow_custom),
                      delimiter=';'
                    ), field_options, field.selector.select.custom_value == True)
                else:
                  if field.default is not None: default_value = type(field_options[0].value)(field.default) if len(field_options) > 0 else field.default
                  if len(field_all_options) > 25 or not are_all_strings or field.selector.select.custom_value == True:
                    autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=field_options)
                    field_type = str
                  else:
                    field_type = Literal[*field_all_options]
                  transformers[field_id] = partial(require_choice, all_choices=field_options, allow_custom=field.selector.select.custom_value == True) # Confirm if the choice is valid
                
              elif field.selector.target is not None: # ServiceFieldSelectorTarget
                field_type = str
                autocomplete_replacements[field_id] = partial(
                  multiple_autocomplete,
                  func=partial(
                    label_floor_area_device_entity_autocomplete,
                    entity_filter=to_list(service.target.entity),
                    device_filter=to_list(service.target.device)
                  )
                )
                transformers[field_id] = lambda result, interaction: self.parse_targets(transform_multiple_autocomplete(result, interaction))

              elif field.selector.template is not None: # ServiceFieldSelectorTemplate
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif field.selector.text is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.text.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=None,
                      allow_custom=True
                    )
                    transformers[field_id] = partial(transform_multiple_autocomplete, default_transform=None)
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str)) # Needs to be customly split...
                  
              elif field.selector.time is not None: # ServiceFieldSelectorTime
                field_type = str
                if field.default is not None: default_value = str(field.default)
                additional_description = 'HH:MM' if field.selector.time.no_second == True else 'HH:MM:SS'

              elif self.ALLOW_UNSUPPORTED and field.selector.addon is not None: # ServiceFieldSelectorAddon
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif self.ALLOW_UNSUPPORTED and field.selector.assist_pipeline is not None: # ServiceFieldSelectorAssistPipeline
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif self.ALLOW_UNSUPPORTED and field.selector.backup_location is not None: # ServiceFieldSelectorBackupLocation
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif self.ALLOW_UNSUPPORTED and field.selector.config_entry is not None: # ServiceFieldSelectorConfigEntry
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif self.ALLOW_UNSUPPORTED and field.selector.state is not None: # ServiceFieldSelectorState
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif self.ALLOW_UNSUPPORTED and field.selector.statistic is not None: # ServiceFieldSelectorStatistic
                field_type = str
                if field.default is not None: default_value = str(field.default)

                entity_filter: List[ServiceFieldSelectorEntityFilter] | None = None
                if field.selector.statistic.device_class is not None:
                  entity_filter = [ServiceFieldSelectorEntityFilter.model_validate({ 'device_class': field.selector.statistic.device_class })]

                # Allow selecting actual entity here
                if field.selector.statistic.multiple == True:
                  if self.USE_AUTOCOMPLETE_MULTIPLE:
                    autocomplete_replacements[field_id] = partial(
                      multiple_autocomplete,
                      func=partial(
                        filtered_entity_autocomplete,
                        entity_filter=entity_filter
                      ),
                      allow_custom=True
                    )
                    transformers[field_id] = transform_multiple_autocomplete
                  else:
                    transformers[field_id] = lambda input, _: transform_multiple(input, lambda x: isinstance(x, str), delimiter=';')
                else:
                  autocomplete_replacements[field_id] = partial(
                    filtered_entity_autocomplete,
                    entity_filter=entity_filter
                  )

              elif self.ALLOW_UNSUPPORTED and field.selector.theme is not None: # ServiceFieldSelectorTheme
                field_type = str
                if field.default is not None: default_value = str(field.default)
              
              else:
                self.bot.logger.error("Unknown selector - %s %s %s %s", domain.domain, service_id, field_id, str(field.selector))
                raise Exception('Unknown selector')

              if not is_hidden:
                # Add the parameter to function signature
                is_field_required = field.required == True

                # Adjust the field name and description
                all_params.add(field_id)
                if field.name is not None:
                  renames[field_id] = field.name
                
                field_description_components: List[str] = []
                if field.example is not None:
                  field_description_components.append(f'(eg. {str(field.example)})')
                if field.description is not None:
                  field_description_components.append(str(field.description))
                if additional_description is not None:
                  field_description_components.append(str(additional_description))
                descriptions[field_id] = " - ".join(field_description_components)
                if len(descriptions[field_id]) == 0: descriptions[field_id] = '-'

                parameter_data = {
                  'name': field_id,
                  'kind': inspect.Parameter.KEYWORD_ONLY,
                  'annotation': Optional[field_type] if not is_field_required else field_type
                }

                if default_value is not None:
                  parameter_data['default'] = default_value
                elif not is_field_required:
                  parameter_data['default'] = None

                params.append(inspect.Parameter(**parameter_data))

      # Adjust the handler function signature
      handler.__signature__ = inspect.Signature(params)

      # Create the commands
      service_description = str(service.description) if service.description is not None else '-'
      if len(service_description) == 0: service_description = '-'
      
      # Deduplicate renames
      set_already_renamed: Set[str] = set()
      final_renames: Dict[str, str] = {}
      for i, v in renames.items():
        v = shorten_argument_rename(v)
        if i != v and v not in all_params:
          if v not in set_already_renamed:
            set_already_renamed.add(v)
            final_renames[i] = v

      group.command(
        name=service_id,
        description=shorten(service.description, 100)
      )(
        app_commands.autocomplete(**{
          i: require_permission_autocomplete(v, check_role=True)
          for i, v in autocomplete_replacements.items()
        })( # Apply the autocompletes
          app_commands.rename(**final_renames)( # Apply the renames
            app_commands.describe(**{ i: shorten(v, 100) for i, v in descriptions.items() })(handler)
          )
        )
      )

    except Exception as e:
      self.bot.logger.error("Failed to add service - %s %s %s %s", domain.domain, service_id, type(e), e)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))