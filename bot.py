import os
import logging
from cachetools import TTLCache

from homeassistant_api import Client as HAClient

import discord
from discord.ext import commands

class HASSDiscordBot(commands.Bot):
  def __init__(self, logger: logging.Logger) -> None:
    super().__init__(
      command_prefix=commands.when_mentioned_or("!"),
      intents=discord.Intents.default()
    )

    self.conversation_cache = TTLCache(maxsize=100, ttl=15*60)
    self.homeassistant_data_cache = TTLCache(maxsize=100, ttl=15*60)

    self.homeassistant_client = HAClient(
      os.getenv("HOMEASSISTANT_API_URL"),
      os.getenv("HOMEASSISTANT_TOKEN")
    )
    self.homeassistant_url = os.getenv("HOMEASSISTANT_URL")

    discord_guild_id_env = os.getenv("DISCORD_GUILD_ID")
    self.discord_main_guild_id = int(discord_guild_id_env) if discord_guild_id_env is not None else None

    self.MAX_AUTOCORRECT_CHOICES = 25
    self.SIMILARITY_TOLERANCE = 0.2 # Only display items with score >= max_score * (1 - SIMILARITY_TOLERANCE)

    self.logger = logger

  async def load_cogs(self) -> None:
    COG_EXTENSION = ".py"
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
      if file.endswith(COG_EXTENSION):
        cog_name = file[:-len(COG_EXTENSION)]
        try:
          await self.load_extension(f"cogs.{cog_name}")
          self.logger.info(f"Loaded cog {cog_name}")
        except Exception as e:
          self.logger.error(
            f"Failed to load the cog {cog_name} - {type(e).__name__}\n{e}"
          )
  async def setup_hook(self):
    await self.load_cogs()

    return await super().setup_hook()