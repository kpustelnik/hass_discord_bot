from typing import Optional, Literal, List, Dict, Any, Callable, Set
import discord
from discord.ext import commands
from discord import app_commands
import yaml
import json
import inspect
from helpers import shorten, shorten_argument_rename
import datetime
import re

from bot import HASSDiscordBot
from autocompletes import filtered_device_autocomplete, filtered_entity_autocomplete, require_choice, label_area_device_entity_autocomplete, choice_autocomplete
from functools import partial
from enums.emojis import Emoji
from models.ServiceModel import DomainModel, ServiceModel, ServiceFieldCollection, ServiceField
from homeassistant_api.errors import RequestError

class Services(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    self.WHITELISTED_SERVICES = [
      ['light', 'turn.*']
    ]

    try:
      ha_domains: List[DomainModel] = self.bot.homeassistant_client.cache_custom_get_domains()
      for domain in ha_domains:
        group = app_commands.Group(
          name=domain.domain,
          description=f"{domain.domain} services (actions)",
          guild_ids=[self.bot.discord_main_guild_id] if self.bot.discord_main_guild_id is not None else None
        )

        any_added = False
        for service_id, service in domain.services.items():
          if self.check_whitelist(domain.domain, service_id):
            any_added = True
            self.create_service_command(group, domain, service_id, service)

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
  
  def create_service_command(self, group, domain: DomainModel, service_id: str, service: ServiceModel):
    # Create handler function
    constants: Dict[str, Any] = {}
    transformers: Dict[str, Callable[[Any], Any]] = {}
    renames: Dict[str, str] = {}
    async def handler(interaction: discord.Interaction, **kwargs):
      if not await self.bot.check_user_guild(interaction, check_role=True):
        return
    
      await interaction.response.defer()

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

        match target:
          case s if s.startswith('AREA$'):
            final_kwargs['area_id'] = s[len('AREA$'):]
          case s if s.startswith('DEVICE$'):
            final_kwargs['device_id'] = s[len('DEVICE$'):]
          case s if s.startswith('ENTITY$'):
            final_kwargs['entity_id'] = s[len('ENTITY$'):]
          case s if s.startswith('LABEL$'):
            final_kwargs['label_id'] = s[len('LABEL$'):]

      # Send the request
      try:
        try:
          changed_entities, response_data = self.bot.homeassistant_client.custom_trigger_service_with_response(
            domain.domain,
            service_id,
            **final_kwargs
          )
        except RequestError:
          response_data = None
          changed_entities = self.bot.homeassistant_client.custom_trigger_services(
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
      autocomplete_replacements["service_action_target"] = partial(  # Ugly solution but it works
        label_area_device_entity_autocomplete,
        domain=service.target.entity.domain,
        supported_features=service.target.entity.supported_features,
        integration=service.target.entity.integration
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

              is_hidden = False
              field_type = None
              default_value = None
              if field.selector.text is not None: # ServiceFieldSelectorText
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

              elif field.selector.duration is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.duration.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.entity is not None: # ServiceFieldSelectorEntity
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.entity.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                else:
                  autocomplete_replacements[field_id] = partial(filtered_entity_autocomplete, integration=field.selector.entity.integration, domain=field.selector.entity.domain)

              elif field.selector.select is not None: # ServiceFieldSelectorSelect 
                field_options = field.selector.select.options
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

              elif field.selector.boolean is not None: # ServiceFieldSelectorBoolean
                field_type = bool
                if field.default is not None: default_value = bool(field.default)

              elif field.selector.theme is not None: # ServiceFieldSelectorTheme
                field_type = str
                if field.default is not None: default_value = str(field.default)

              elif field.selector.color_temp is not None: # ServiceFieldSelectorNumber
                subtype = float if field.selector.color_temp is not None and isinstance(field.selector.color_temp, int) and field.selector.color_temp.step != 1 else int
                if field.selector.color_temp.min is not None or field.selector.color_temp.max is not None:
                  val_max = field.selector.color_temp.max
                  if val_max is not None and val_max > 9007199254740991:
                    val_max = 9007199254740991
                  field_type = app_commands.Range[subtype, field.selector.color_temp.min, val_max]
                else:
                  field_type = subtype
                if field.default is not None: default_value = subtype(field.default)

              elif field.selector.datetime is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.datetime.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                  
              elif field.selector.time is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.time.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.date is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.date.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.statistic is not None: # ServiceFieldSelectorEntity
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.statistic.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
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
                  
              elif field.selector.color_rgb is not None: # ServiceFieldSelectorObject
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, int) and x >= 0 and x <= 255, minlen=3, maxlen=3)

              elif field.selector.device is not None: # ServiceFieldSelectorDevice
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.device.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))
                else:
                  autocomplete_replacements[field_id] = partial(filtered_device_autocomplete, integration=field.selector.device.integration, domain=field.selector.device.domain)


              elif field.selector.icon is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
                if field.selector.icon.multiple == True:
                  transformers[field_id] = lambda input: Services.transform_multiple(input, lambda x: isinstance(x, str))

              elif field.selector.constant is not None: # ServiceFieldSelectorConstant
                field_type = type(field.selector.constant.value)
                if field.default is not None:
                  default_value = field.default # For further consideration...
                else:
                  default_value = False
                  
                constants[field_id] = field.selector.constant.value

              else:
                self.bot.logger.error("Unknown selector", domain.domain, service_id, field_id)
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

      cmd = group.command(
        name=service_id,
        description=shorten(service.description, 100)
      )(
        app_commands.rename(**final_renames)(
          app_commands.describe(**{ i: shorten(v, 100) for i, v in descriptions.items() })(handler)
        )
      )

      # Apply the autocompletes
      for i, func in autocomplete_replacements.items():
        cmd._params[i].autocomplete = func

    except Exception as e:
      self.bot.logger.error("Failed to add service", domain.domain, service_id, type(e), e)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))