import urllib.parse
import datetime

import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from helpers import add_param
from autocompletes import Autocompletes

class Entities(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot
    self.OMMITED_ENTITY_ATTRIBUTES = ["friendly_name"]

    self.bot.tree.add_command(
      app_commands.Command(
        name="get_entity",
        description="Retrieves information about an entity from Home Assistant",
        callback=self.get_entity
      ), 
      guild=discord.Object(self.bot.discord_main_guild_id) if self.bot.discord_main_guild_id is not None else None) # Get entity command

  @app_commands.autocomplete(entity_id=Autocompletes.entity_autocomplete)
  @app_commands.describe(entity_id="HomeAssistant entity identifier")
  @app_commands.checks.has_role(1398385337423626281) # TODO: Move to settings
  async def get_entity(self, interaction: discord.Interaction, entity_id: str):
    await interaction.response.defer()

    entity = self.bot.homeassistant_client.get_entity(entity_id=entity_id)
    history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, f"history"), entity_id=entity.entity_id)

    friendly_name = self.bot.homeassistant_client.get_entity_friendlyname(entity)
    embed = discord.Embed(
      title=f"{friendly_name if friendly_name is not None else "?"}",
      description=entity.entity_id,
      color=discord.Colour.default(),
      timestamp=datetime.datetime.now()
    )

    embed.add_field(name="State", value=entity.state)
    embed.add_field(name="Last changed", value=str(entity.last_changed))
    embed.add_field(name="Last updated", value=str(entity.last_updated))
    embed.add_field(name="", value="Attributes", inline=False)
    for name, value in filter(lambda x: x[0] not in self.OMMITED_ENTITY_ATTRIBUTES, entity.attributes.items()):
      embed.add_field(name=name, value=str(value))

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Entity history", url=history_url))

    await interaction.followup.send(embed=embed, view=view)


async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Entities(bot))