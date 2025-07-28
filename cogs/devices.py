from discord.ext import commands
from discord import app_commands
import discord
import urllib
import datetime

from bot import HASSDiscordBot
from helpers import add_param
from autocompletes import Autocompletes

class Devices(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    self.bot.tree.add_command(
      app_commands.Command(
        name="get_device",
        description="Retrieves information about a device from Home Assistant",
        callback=self.get_device
      ), 
      guild=discord.Object(self.bot.discord_main_guild_id) if self.bot.discord_main_guild_id is not None else None) # Get device command

  @app_commands.autocomplete(device_id=Autocompletes.device_autocomplete)
  @app_commands.describe(device_id="HomeAssistant device identifier")
  @app_commands.checks.has_role(1398385337423626281) # TODO: Move to settings
  async def get_device(self, interaction: discord.Interaction, device_id: str):
    await interaction.response.defer()
    
    device = self.bot.homeassistant_client.custom_get_device(device_id=device_id)
    history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, f"history"), device_id=device.id)
    config_url = urllib.parse.urljoin(self.bot.homeassistant_url, f"config/devices/device/{device.id}")

    embed = discord.Embed(
      title=device.name,
      description=device.id,
      color=discord.Colour.default(),
      timestamp=datetime.datetime.now()
    )

    embed.add_field(name="Entities", value="\n".join(device.entities))

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Device history", url=history_url))
    view.add_item(discord.ui.Button(label="Device config", url=config_url))

    await interaction.followup.send(embed=embed, view=view)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Devices(bot))