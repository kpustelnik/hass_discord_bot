from typing import Optional, Literal, List, Dict
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
      self.bot.logger.error("Failed to fetch domains and create service action commands")
  
  def create_service_command(self, group, domain: DomainModel, service_id: str, service: ServiceModel):
    # Create handler function
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

    if service.target is not None and service.target.entity is not None:
      params.append(
        inspect.Parameter(
          name="service_action_target",
          kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
          annotation=str
        )
      )
      descriptions["service_action_target"] = "HomeAssistant service action target"

    try:

      handler.__signature__ = inspect.Signature(params)

      cmd = group.command(name=service_id)(
        app_commands.describe(**descriptions)(handler)
      )

      if service.target is not None and service.target.entity is not None:
        cmd._params["service_action_target"].autocomplete = partial(Autocompletes.area_device_entity_autocomplete, self) # Ugly solution but it works
    except Exception as e:
      self.bot.logger.error("Failed to add service", domain.domain, service_id, e)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))