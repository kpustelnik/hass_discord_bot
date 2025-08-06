import platform
import os
import logging
from cachetools import TTLCache
from typing import Union

import discord
from discord.ext.commands import Context
from discord import app_commands
from discord.ext import commands, tasks
from haclient import CustomHAClient

from enums.emojis import Emoji

class HASSDiscordBot(commands.Bot):
  def __init__(self, logger: logging.Logger, file_logger: logging.Logger) -> None:
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
    self.discord_special_role_id = int(discord_special_role_id_env) if discord_special_role_id_env is not None else None

    self.status_template = os.getenv("STATUS_TEMPLATE")

    self.MAX_AUTOCOMPLETE_CHOICES = 25
    self.SIMILARITY_TOLERANCE = 0.2 # Only display items with score >= max_score * (1 - SIMILARITY_TOLERANCE)

    self.logger = logger
    self.file_logger = file_logger

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

  @tasks.loop(minutes=1)
  async def status_task(self) -> None:
    if self.status_template is not None:
      try:
        new_status = self.homeassistant_client.format_string(self.status_template)
      except:
        new_status = "Unavailable"
      await self.change_presence(activity=discord.Game(name=new_status))

  @status_task.before_loop
  async def before_status_task(self) -> None:
    await self.wait_until_ready()

  async def setup_hook(self):
    await self.load_cogs()

    self.file_logger.info(f"Logged in as {self.user.name}")
    self.file_logger.info(f"discord.py API version: {discord.__version__}")
    self.file_logger.info(f"Python version: {platform.python_version()}")
    self.file_logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")

    self.status_task.start()
    return await super().setup_hook()

  
  async def on_message(self, message: discord.Message) -> None:
    if message.author == self.user or message.author.bot:
      return # Skip processing own & other bots messages
    await self.process_commands(message)
  
  async def on_app_command_completion(self, interaction: discord.Interaction, command: Union[app_commands.Command, app_commands.ContextMenu]):
    executed_command = interaction.command.name
    if interaction.guild is not None:
      self.file_logger.info(f"CMD {executed_command} in {interaction.guild.name} (ID: {interaction.guild.id}) by {interaction.user} (ID: {interaction.user.id})")
    else:
      self.file_logger.info(f"CMD {executed_command} in DM by {interaction.user} (ID: {interaction.user.id})")

  async def on_command_completion(self, context: Context) -> None:
    # Log commands usage
    full_command_name = context.command.qualified_name
    split = full_command_name.split(" ")
    executed_command = str(split[0])
    if context.guild is not None:
      self.file_logger.info(f"CMD {executed_command} in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})")
    else:
      self.file_logger.info(f"CMD {executed_command} in DM by {context.author} (ID: {context.author.id})")

  async def on_command_error(self, context: Context, error) -> None:
    pass
    # https://discordpy.readthedocs.io/en/stable/ext/commands/api.html

  
  async def on_ready(self):
    self.file_logger.info("Bot is ready")
    try:
      synced = await self.tree.sync()
      self.file_logger.info(f"Synced {len(synced)} commands")
      if self.discord_main_guild_id is not None:
        synced_guild = await self.tree.sync(guild=discord.Object(self.discord_main_guild_id))
        self.file_logger.info(f"Synced {len(synced_guild)} guild commands")
    except Exception as e:
      self.logger.error("Sync error", e)
  
  async def check_user_guild(self, interaction: discord.Interaction, check_role=False) -> bool:
    respond = interaction.type == discord.InteractionType.application_command

    if await self.is_owner(interaction.user): # The bot's owner should always be able to run the command
      return True

    if self.discord_main_guild_id is None: # Guild is not limited, the command can be run
      return True

    guild = self.get_guild(self.discord_main_guild_id)
    if guild is None and interaction.guild is not None and interaction.guild.id == self.discord_main_guild_id:
      # If guild can't be fetched but the interaction was run in correct guild, assign it to variable
      guild = interaction.guild

    if guild is None: # Guild can't be found
      if respond: await interaction.response.send_message(f"{Emoji.ERROR} Guild was not found and the command was not run in correct guild.", ephemeral=True)
      return False
    
    try:
      member = await guild.fetch_member(interaction.user.id) # Fetch the guild member
    except Exception as e: # Failed to fetch the member
      if respond: await interaction.response.send_message(f"{Emoji.ERROR} You are not in required guild or bot is not able to verify that.", ephemeral=True)
      return False

    if member is None or member.pending:
      if respond: await interaction.response.send_message(f"{Emoji.ERROR} You are not in required guild or you are still pending.", ephemeral=True)
      return False

    if check_role and self.discord_special_role_id is not None: # Also check if the executor has correct role
      if not any(role.id == self.discord_special_role_id for role in member.roles):
        if respond: await interaction.response.send_message(f"{Emoji.ERROR} You need <@&{self.discord_special_role_id}> role to run this command.", ephemeral=True)
        return False

    return True # Assume the command can be run