from discord.ext import commands
from discord import app_commands
import discord
from typing import List
import urllib
import datetime

from bot import HASSDiscordBot
from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name, add_param

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

  async def device_autocomplete(
      self,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_devices = self.bot.homeassistant_client.cache_custom_get_devices()
      if homeassistant_devices is None:
        raise Exception("No devices were returned")
    except Exception as e:
      print("Failed to fetch devices", e)
      return []
      
    target_tokens = tokenize(current_input)
    choice_list = [
      (
        max(
          fuzzy_keyword_match_with_order(tokenize(device.id), target_tokens),
          fuzzy_keyword_match_with_order(tokenize(device.name), target_tokens)
        ),
        app_commands.Choice(
          name=shorten_option_name(f"{device.name} ({device.id})"),
          value=device.id
        )
      )
      for device in homeassistant_devices
    ]
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - self.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:self.bot.MAX_AUTOCORRECT_CHOICES] if x[0] >= min_score]

  @app_commands.autocomplete(device_id=device_autocomplete)
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