from typing import Optional, Literal, List, Dict, Any, Callable, Set
import discord
from discord.ext import commands
from discord import app_commands
import yaml
import json
import inspect
from helpers import shorten, shorten_argument_rename
import datetime

from bot import HASSDiscordBot
from autocompletes import Autocompletes
from functools import partial
from enums.emojis import Emoji
from models.ServiceModel import DomainModel, ServiceModel, ServiceFieldCollection, ServiceField
from homeassistant_api.errors import RequestError

# TODO: Parse object with yaml, and then json

class Services(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    try:
      ha_domains: List[DomainModel] = self.bot.homeassistant_client.cache_custom_get_domains()
      for domain in ha_domains:
        group = app_commands.Group(
          name=domain.domain,
          description=f"{domain.domain} services (actions)",
          guild_ids=[self.bot.discord_main_guild_id] if self.bot.discord_main_guild_id is not None else None
        )

        for service_id, service in domain.services.items():
          self.create_service_command(group, domain, service_id, service)

        self.bot.tree.add_command(group)
    except Exception as e:
      self.bot.logger.error("Failed to fetch domains and create service action commands", type(e), e)

  @staticmethod
  def transform_object(src: str) -> Any:
    try:
        return yaml.safe_load(src)
    except yaml.YAMLError:
        try:
            return json.loads(src)
        except json.JSONDecodeError:
            raise ValueError("Incorrect input")
  
  def create_service_command(self, group, domain: DomainModel, service_id: str, service: ServiceModel):
    # Create handler function
    transformers: Dict[str, Callable[[Any], Any]] = {}
    async def handler(interaction: discord.Interaction, **kwargs):
      await interaction.response.defer()

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
        description='',
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      embed.add_field(
        name=f'{Emoji.SUCCESS} Modified entities',
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
    renames: Dict[str, str] = {}
    autocomplete_replacements: Dict[str, Any] = {}

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
      autocomplete_replacements["service_action_target"] = partial(Autocompletes.area_device_entity_autocomplete, self) # Ugly solution but it works
  # TODO: target.entity.
  # domain: Optional[List[str]] = None
  # supported_features: Optional[List[int]] = None # Bitset flags
  # integration: Optional[str] = None

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

              field_type = None
              default_value = None
              if field.selector.text is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.config_entry is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.conversation_agent is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.number is not None: # ServiceFieldSelectorNumber
                if field.selector.number.min is not None or field.selector.number.max is not None:
                  field_type = app_commands.Range[float, field.selector.number.min, field.selector.number.max]
                else:
                  field_type = float # TODO
                if field.default is not None: default_value = float(field.default)
              elif field.selector.duration is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.entity is not None: # ServiceFieldSelectorEntity
                field_type = str # TODO
                autocomplete_replacements[field_id] = partial(Autocompletes.entity_autocomplete, self)
                if field.default is not None: default_value = field.default
              elif field.selector.select is not None: # ServiceFieldSelectorSelect 
                field_options = field.selector.select.options # TODO: Implement autocomplete
                if len(field_options) > 25:
                  field_type = str
                  autocomplete_replacements[field_id] = partial(Autocompletes.choice_autocomplete, self, all_choices=field_options)
                  transformers[field_id] = lambda input: Autocompletes.require_choice(input, field_options)
                else:
                  field_type = Literal[*field_options]
                if field.default is not None: default_value = type(field_options[0])(field.default) if len(field_options) > 0 else field.default
              elif field.selector.boolean is not None: # ServiceFieldSelectorBoolean
                field_type = bool
                if field.default is not None: default_value = bool(field.default)
              elif field.selector.theme is not None: # ServiceFieldSelectorTheme
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.color_temp is not None: # ServiceFieldSelectorNumber
                field_type = float
                if field.default is not None: default_value = float(field.default)
              elif field.selector.datetime is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.time is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.date is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.statistic is not None: # ServiceFieldSelectorEntity
                field_type = str
                if field.default is not None: default_value = str(field.default)
                autocomplete_replacements[field_id] = partial(Autocompletes.entity_autocomplete, self)
              elif field.selector.object is not None: # ServiceFieldSelectorObject
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = self.transform_object
              elif field.selector.template is not None: #ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.color_rgb is not None: # ServiceFieldSelectorObject
                field_type = str
                if field.default is not None: default_value = str(field.default)
                transformers[field_id] = self.transform_object
              elif field.selector.device is not None: # ServiceFieldSelectorDevice
                field_type = str
                if field.default is not None: default_value = str(field.default)
                autocomplete_replacements[field_id] = partial(Autocompletes.device_autocomplete, self)
              elif field.selector.icon is not None: # ServiceFieldSelectorText
                field_type = str
                if field.default is not None: default_value = str(field.default)
              elif field.selector.constant is not None: # ServiceFieldSelectorConstant
                field_type = type(field.selector.constant.value)
                if field.default is not None: default_value = field.default
                # TODO: Block editing?
              else:
                self.bot.logger.error("Unknown selector", domain.domain, service_id, field_id)
                raise Exception('Unknown selector')
              
              # Adjust the field name and description
              if field.name is not None:
                renames[field_id] = field.name
              
              field_description_components: List[str] = []
              if field.example is not None:
                field_description_components.append(f'(eg. {str(field.example)})')
              if field.description is not None:
                field_description_components.append(str(field.description))
              descriptions[field_id] = " - ".join(field_description_components)
              if len(descriptions[field_id]) == 0: descriptions[field_id] = '-'

              # Add the parameter to function signature
              params.append(inspect.Parameter(
                name=field_id,
                kind=inspect.Parameter.KEYWORD_ONLY,
                annotation=Optional[field_type] if field.required == False else field_type,
                default=default_value
              ))

      # Adjust the handler function signature
      handler.__signature__ = inspect.Signature(params)

      # Create the commands
      service_description = str(service.description) if service.description is not None else '-'
      if len(service_description) == 0: service_description = '-'
      
      # Deduplicate renames
      set_already_renamed: Set[str] = set()
      final_renames = {}
      for i, v in renames.items():
        if i != v:
          v = shorten_argument_rename(v)
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
      if service.target is not None and service.target.entity is not None:
        for i, func in autocomplete_replacements.items():
          cmd._params[i].autocomplete = func

    except Exception as e:
      self.bot.logger.error("Failed to add service", domain.domain, service_id, type(e), e)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))