import os
import logging
from cachetools import TTLCache

import discord
from discord.ext import commands
from haclient import CustomHAClient

from enums.emojis import Emoji

class HASSDiscordBot(commands.Bot):
  def __init__(self, logger: logging.Logger) -> None:
    super().__init__(
      command_prefix=commands.when_mentioned_or("!"),
      intents=discord.Intents.default()
    )

    self.conversation_cache = TTLCache(maxsize=100, ttl=15*60)

    self.homeassistant_client = CustomHAClient(
      os.getenv("HOMEASSISTANT_API_URL"),
      os.getenv("HOMEASSISTANT_TOKEN"),
      use_async=False
    )
    self.homeassistant_url = os.getenv("HOMEASSISTANT_URL")

    discord_guild_id_env = os.getenv("DISCORD_GUILD_ID")
    self.discord_main_guild_id = int(discord_guild_id_env) if discord_guild_id_env is not None else None
    discord_special_role_id_env = os.getenv("DISCORD_SPECIAL_ROLE_ID")
    self.discord_special_role_id = discord_special_role_id_env

    self.MAX_AUTOCOMPLETE_CHOICES = 25
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
  
  async def on_ready(self):
    self.logger.info("Bot is ready")
    try:
      synced = await self.tree.sync()
      self.logger.info(f"Synced {len(synced)} commands")
      if self.discord_main_guild_id is not None:
        synced_guild = await self.tree.sync(guild=discord.Object(self.discord_main_guild_id))
        self.logger.info(f"Synced {len(synced_guild)} guild commands")
    except Exception as e:
      self.logger.error("Sync error", e)
  
  async def check_user_role(self, interaction: discord.Interaction) -> bool:
    if not interaction.guild:
      await interaction.response.send_message(f"{Emoji.ERROR} Command needs to be executed in guild.", ephemeral=True)
      return False
    
    member = interaction.user
    if not isinstance(member, discord.Member):
      member = await interaction.guild.fetch_member(interaction.user.id)

    if self.discord_special_role_id is not None and not any(role.id == self.discord_special_role_id for role in member.roles):
      await interaction.response.send_message(f"{Emoji.ERROR} You need <@{self.discord_special_role_id}> role to run this command.", ephemeral=True)
      return False

    return True