from typing import Optional, Literal, List, Dict, Any, Callable, Set
import discord
from discord.ext import commands
from discord import app_commands
import yaml
import json
import inspect
from helpers import shorten, shorten_argument_rename, to_list, is_matching
import datetime
import re
import pycountry

from bot import HASSDiscordBot
from autocompletes import icon_autocomplete, filtered_label_autocomplete, filtered_floor_autocomplete, filtered_area_autocomplete, filtered_device_autocomplete, filtered_entity_autocomplete, require_choice, label_floor_area_device_entity_autocomplete, choice_autocomplete, require_permission_autocomplete
from functools import partial
from enums.emojis import Emoji
from models.ServiceModel import DomainModel, ServiceModel, ServiceFieldSelectorDevice, ServiceFieldSelectorEntity, ServiceFieldCollection, ServiceField, ServiceFieldSelectorSelectOption, ServiceFieldSelectorEntityFilter, replacePlainSelectorOptions, replaceLegacyDeviceSelector, replaceLegacyEntitySelector
from homeassistant_api.errors import RequestError

class Services(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    self.WHITELISTED_SERVICES = [
      ['light', 'turn.*']
    ]

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
      self.bot.logger.error("Failed to fetch domains and create service action commands", type(e), e)

  def check_whitelist(self, domain_id, service_id) -> bool:
    for tmpl_domain_id, tmpl_service_id in self.WHITELISTED_SERVICES:
      if re.match(tmpl_domain_id, domain_id) is not None and re.match(tmpl_service_id, service_id):
        return True
    return False

  @staticmethod
  def transform_object(src: str) -> Any:
    try:
        return yaml.safe_load(src)
    except yaml.YAMLError:
        try:
            return json.loads(src)
        except json.JSONDecodeError:
            raise ValueError("Incorrect input")
        
  @staticmethod
  def transform_multiple(src: str, checker: Callable[[Any], bool], minlen: Optional[int] = None, maxlen:Optional[int] = None) -> List[Any]:
    parsed_object = Services.transform_object(src)
    if not isinstance(parsed_object, list):
      raise ValueError("Input is not a list")
    
    if maxlen is not None and len(parsed_object) > maxlen:
      raise ValueError("Too many values")
    if minlen is not None and len(parsed_object) < minlen:
      raise ValueError("Too few values")
    
    for value in parsed_object:
      if not checker(value):
        raise ValueError("Incorrect input elements")
    return parsed_object
  
  async def create_service_command(self, group, domain: DomainModel, service_id: str, service: ServiceModel):
    # Create handler function
    constants: Dict[str, Any] = {}
    transformers: Dict[str, Callable[[Any], Any]] = {}
    renames: Dict[str, str] = {}
    async def handler(interaction: discord.Interaction, **kwargs):
      if not await self.bot.check_user_guild(interaction, check_role=True):
        return
    
      await interaction.response.defer(thinking=True)

      # Apply the constants
      for id, value in constants.items():
        if kwargs[id] == True:
          kwargs[id] = value
        else:
          del kwargs[id]

      # Apply transformers
      try:
        final_kwargs = {
          name: transformers[name](value) if name in transformers else value
          for name, value in kwargs.items() if value is not None
        }
      except Exception as e:
        await interaction.followup.send(f'{Emoji.ERROR} {str(e)}', ephemeral=True)
        return

      # Parse the target if available
      if 'service_action_target' in final_kwargs:
        target = final_kwargs['service_action_target']
        del final_kwargs['service_action_target']

        match target: # Targets could also be lists
          case s if s.startswith('AREA$'):
            final_kwargs['area_id'] = s[len('AREA$'):]
          case s if s.startswith('DEVICE$'):
            final_kwargs['device_id'] = s[len('DEVICE$'):]
          case s if s.startswith('ENTITY$'):
            final_kwargs['entity_id'] = s[len('ENTITY$'):]
          case s if s.startswith('FLOOR$'):
            final_kwargs['floor_id'] = s[len('FLOOR$'):]
          case s if s.startswith('LABEL$'):
            final_kwargs['label_id'] = s[len('LABEL$'):]

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
        self.bot.logger.error('Failed to send action to HomeAssistant', type(e), e)
        await interaction.followup.send(f'{Emoji.ERROR} Failed to send action to HomeAssistant', ephemeral=True)
        return

      # Create embed
      embed = discord.Embed(
        title=f"{domain.domain} > {service.name} execution",
        description=f'{Emoji.SUCCESS} Service action succeeded',
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      for i, v in kwargs.items():
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
        self.bot.logger.error('Failed to construct the response', type(e), e)
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
      autocomplete_replacements["service_action_target"] = partial(
        label_floor_area_device_entity_autocomplete,
        entity_filter=to_list(service.target.entity),
        device_filter=to_list(service.target.device)
      )
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
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str)) # TODO: Better support for multiple (autocomplete split by ,)
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

                autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=list(attributes))
                transformers[field_id] = partial(require_choice, all_choices=field_options)

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
                else:
                  field_type = Literal[*field_all_options]
                  
              elif field.selector.color_rgb is not None: # ServiceFieldSelectorColorRGB
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, int) and x >= 0 and x <= 255, minlen=3, maxlen=3)

              elif field.selector.color_temp is not None: # ServiceFieldSelectorColorTemp
                subtype = int
                min_val = field.selector.color_temp.min if field.selector.color_temp.min is not None else field.selector.color_temp.min_mireds
                max_val = field.selector.color_temp.max if field.selector.color_temp.max is not None else field.selector.color_temp.max_mireds
                if min_val is not None or max_val is not None:
                  if max_val is not None and max_val > 9007199254740991:
                    max_val = 9007199254740991
                  if min_val is not None and min_val < -9007199254740991:
                    min_val = -9007199254740991
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
              if field.selector.floor is not None: # ServiceFieldSelectorFloor

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
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                else:
                  autocomplete_replacements[field_id] = partial(filtered_device_autocomplete, device_filter=to_list(new_device_selector.filter), entity_filter=to_list(new_device_selector.entity))

              elif field.selector.entity is not None: # ServiceFieldSelectorEntity | ServiceFieldSelectorEntityLegacy
                new_entity_selector: ServiceFieldSelectorEntity = replaceLegacyEntitySelector(field.selector.entity)
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if new_entity_selector.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                else:
                  autocomplete_replacements[field_id] = partial(filtered_entity_autocomplete, entity_filter=to_list(new_entity_selector.filter))
                
              elif field.selector.floor is not None: # ServiceFieldSelectorFloor
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.floor.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
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
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                else:
                  autocomplete_replacements[field_id] = partial(filtered_label_autocomplete, entity_filter=to_list(field.selector.label.entity), device_filter=to_list(field.selector.label.device))

              # TODO


                '''
              elif field.selector.text is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.text.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.config_entry is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.config_entry.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.conversation_agent is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.conversation_agent.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.number is not None: # ServiceFieldSelectorNumber
                subtype = float if field.selector.number is not None and isinstance(field.selector.number, int) and field.selector.number.step != 1 else int
                if field.selector.number.min is not None or field.selector.number.max is not None:
                  val_max = field.selector.number.max
                  if val_max is not None and val_max > 9007199254740991:
                    val_max = 9007199254740991
                  field_type = app_commands.Range[subtype, field.selector.number.min, val_max]
                else:
                  field_type = subtype
                if field.default is not None: default_value = subtype(field.default)

              elif field.selector.select is not None: # ServiceFieldSelectorSelect
                field_options = field.selector.select.options # TODO
                if field.selector.select.multiple == True:
                  if field.default is not None: default_value = str(field.default)
                  field_type = str
                  transformers[field_id] = partial(lambda c_field_options, input: Services.transform_multiple(
                    input,
                    lambda x: (len(c_field_options) == 0 or isinstance(x, type(c_field_options[0]))) and require_choice(input, all_choices=c_field_options)
                  ), field_options)
                else:
                  if field.default is not None: default_value = type(field_options[0])(field.default) if len(field_options) > 0 else field.default
                  if len(field_options) > 25: # Too many options, use autocomplete
                    field_type = str
                    autocomplete_replacements[field_id] = partial(choice_autocomplete, all_choices=field_options)
                  else: # Use literal type (choices implemented on Discord)
                    field_type = Literal[*field_options]
                  transformers[field_id] = partial(require_choice, all_choices=field_options) # Always confirm if the choice is valid
                
              elif field.selector.target is not None: # ServiceFieldSelectorTarget
                autocomplete_replacements[field_id] = partial(
                  label_floor_area_device_entity_autocomplete,
                  entity_filter=to_list(field.selector.target.entity),
                  device_filter=to_list(field.selector.target.device)
                )

              elif field.selector.template is not None: # ServiceFieldSelectorTemplate
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif field.selector.text is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.text.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                  
              elif field.selector.time is not None: # ServiceFieldSelectorTime
                field_type = str
                if field.default is not None: default_value = str(field.default)
                additional_description = 'HH:MM' if field.selector.time.no_second == True else 'HH:MM:SS'
              
                else:
                  autocomplete_replacements[field_id] = partial(filtered_entity_autocomplete, integration=field.selector.statistic.integration, domain=field.selector.statistic.domain)

              elif field.selector.object is not None: # ServiceFieldSelectorObject
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = self.transform_object
                
              elif field.selector.template is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.template.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.icon is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.icon.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                '''
              else:
                self.bot.logger.error("Unknown selector - %s %s %s", domain.domain, service_id, field_id)
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
      self.bot.logger.error("Failed to add service", domain.domain, service_id, type(e), e)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))