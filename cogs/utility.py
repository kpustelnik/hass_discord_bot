import discord
from discord import app_commands
from discord.ext import commands
import os
from typing import List

from bot import HASSDiscordBot
from enums.emojis import Emoji
from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name

class Utility(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

  async def get_cog_autocomplete_choices(
    self,
    interaction: discord.Interaction,
    current_input: str
  ) -> List[app_commands.Choice[str]]:
    if not await self.bot.is_owner(interaction.user):
      return []

    COG_EXTENSION = ".py"
    cogs_list: List[str] = []
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}"):
      if file.endswith(COG_EXTENSION):
        cog_name = file[:-len(COG_EXTENSION)]
        cogs_list.append(cog_name)

    target_tokens = tokenize(current_input)
    choice_list = [
      (
        fuzzy_keyword_match_with_order(tokenize(cog_name), target_tokens),
        app_commands.Choice(
          name=shorten_option_name(cog_name),
          value=cog_name
        )
      )
      for cog_name in cogs_list
    ]
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - self.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:self.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  @app_commands.command(
      name="reload",
      description="Reloads a cog.",
  )
  @app_commands.autocomplete(cog_name=get_cog_autocomplete_choices)
  @app_commands.describe(cog_name="The name of the cog to reload")
  @app_commands.allowed_installs(guilds=True, users=True)
  @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
  async def reload(self, interaction: discord.Interaction, cog_name: str) -> None:
    if not await self.bot.is_owner(interaction.user):
      await interaction.response.send_message(f"{Emoji.ERROR} Command needs to be executed by the bot's owner.", ephemeral=True)
      return

    extension_name = f"cogs.{cog_name}"
    try:
      await interaction.response.defer()
      try:
        await self.bot.reload_extension(extension_name)
        await interaction.followup.send(f"{Emoji.SUCCESS} Successfully reloaded the extension.")
      except Exception:
        await interaction.followup.send(f"{Emoji.ERROR} Failed to reload the `{cog_name}` cog.", ephemeral=True)
    except Exception as e:
      self.bot.logger.error("General error", e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)
    

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Utility(bot))