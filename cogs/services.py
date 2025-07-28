from typing import Optional, Literal, List, Dict, Any, Callable
import discord
from discord.ext import commands
from discord import app_commands
import yaml
import json
import inspect

from bot import HASSDiscordBot
from autocompletes import Autocompletes
from functools import partial
from enums.emojis import Emoji
from models.ServiceModel import DomainModel, ServiceModel

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
    async def handler(interaction: discord.Interaction, entity_id: str, **kwargs):
      await interaction.response.defer()

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
      renames["service_action_target"] = "Service action target"
      descriptions["service_action_target"] = "HomeAssistant service action target"
      autocomplete_replacements["service_action_target"] = partial(Autocompletes.area_device_entity_autocomplete, self) # Ugly solution but it works
  # TODO: target.entity.
  # domain: Optional[List[str]] = None
  # supported_features: Optional[List[int]] = None # Bitset flags
  # integration: Optional[str] = None

    try:
      if service.fields is not None:
        fields_queue = [service.fields]

        while len(fields_queue) > 0:
          fields = fields_queue.pop(0)
          for i, (field_id, field) in enumerate(fields.items()):
              if field.selector is None: # Ignore fields that wouldn't be visible in DevTools UI Action runner
                continue

              field_type = None
              if field.selector.text is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.config_entry is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.conversation_agent is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.number is not None: # ServiceFieldSelectorNumber
                if field.selector.number.min is not None or field.selector.number.max is not None:
                  field_type = app_commands.Range[float, field.selector.number.min, field.selector.number.max]
                else:
                  field_type = float # TODO
              elif field.selector.duration is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.entity is not None: # ServiceFieldSelectorEntity
                field_type = str # TODO
                autocomplete_replacements[field_id] = partial(Autocompletes.entity_autocomplete, self)
              elif field.selector.select is not None: # ServiceFieldSelectorSelect 
                field_type = Literal[*field.selector.select.options]
              elif field.selector.boolean is not None: # ServiceFieldSelectorBoolean
                field_type = bool
              elif field.selector.theme is not None: # ServiceFieldSelectorTheme
                field_type = str
              elif field.selector.color_temp is not None: # ServiceFieldSelectorNumber
                field_type = float
              elif field.selector.datetime is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.time is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.date is not None: # ServiceFieldSelectorText
                field_type = str
              elif field.selector.statistic is not None: # ServiceFieldSelectorEntity
                field_type = str
                autocomplete_replacements[field_id] = partial(Autocompletes.entity_autocomplete, self)
              elif field.selector.object is not None: # ServiceFieldSelectorObject
                field_type = str
                transformers[field_id] = self.transform_object
              elif field.selector.template is not None: #ServiceFieldSelectorText
                field_type = str
              elif field.selector.color_rgb is not None: # ServiceFieldSelectorObject
                field_type = str
                transformers[field_id] = self.transform_object
              elif field.selector.device is not None: # ServiceFieldSelectorDevice
                field_type = str
                autocomplete_replacements[field_id] = partial(Autocompletes.device_autocomplete, self)
              elif field.selector.icon is not None: # ServiceFieldSelectorText
                field_type = str
              else:
                self.bot.logger("Unknown selector", domain.domain, service_id)
              
              # Adjust the field name and description
              if field.name is not None:
                renames[field_id] = field.name
              
              field_description_components: List[str] = []
              if field.example is not None:
                field_description_components.append(f'(eg. {str(field.example)})')
              if field.description is not None:
                field_description_components.append(str(field.description))
              descriptions[field_id] = " - ".join(field_description_components)

              # Add the parameter to function signature
              params.append(inspect.Parameter(
                  name=field_id,
                  kind=inspect.Parameter.KEYWORD_ONLY,
                  annotation=Optional[field_type] if field.required == False else field_type
              ))

      # Adjust the handler function signature
      handler.__signature__ = inspect.Signature(params)

      # Create the commands
      cmd = group.command(
        name=service_id,
        description=service.description
      )(
        app_commands.describe(**descriptions)(handler)
      )

      # Apply the autocompletes
      if service.target is not None and service.target.entity is not None:
        for i, func in autocomplete_replacements.items():
          cmd._params[i].autocomplete = func

    except Exception as e:
      self.bot.logger.error("Failed to add service", domain.domain, service_id, e)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))