from typing import Optional, Literal

import discord
from discord.ext import commands
from discord import app_commands

from bot import HASSDiscordBot
from autocompletes import Autocompletes
from functools import partial

# TODO: Parse object with yaml, and then json

class Services(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot
  
    ha_domains = self.bot.homeassistant_client.cache_custom_get_domains()
    for domain in ha_domains.values():
      group = app_commands.Group(
        name=domain.domain_id,
        description="Some description",
        guild_ids=[self.bot.discord_main_guild_id] if self.bot.discord_main_guild_id is not None else None
      )

      for service in domain.services.values():
        self.create_service_command(group, domain, service)
      self.bot.tree.add_command(group)
  
  def create_service_command(self, group, domain, service):
    pass

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Services(bot))