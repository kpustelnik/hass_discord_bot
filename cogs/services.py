from typing import Optional, Literal, List
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
    async def handler(interaction: discord.Interaction, entity_id: str, **kwargs):
    handler.__name__ = f"{service_id}"  # required to avoid duplicate names
    handler.__qualname__ = handler.__name__
    
    params = [
        inspect.Parameter(
            name="interaction",
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=discord.Interaction
        ),
    ]

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))