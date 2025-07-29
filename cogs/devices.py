from discord.ext import commands
from discord import app_commands
import discord
import urllib
import datetime
from typing import List

from bot import HASSDiscordBot
from helpers import add_param, find, shorten_embed_value
from autocompletes import Autocompletes
from models.DeviceModel import DeviceModel
from models.AreaModel import AreaModel
from models.EntityModel import EntityModel
from enums.emojis import Emoji

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
    try:
      await interaction.response.defer()

      try:
        device_data: DeviceModel | None = self.bot.homeassistant_client.custom_get_device(device_id=device_id)
        if device_data is None:
          return await interaction.followup.send(f"{Emoji.ERROR} No device found.", ephemeral=True)
      except Exception as e:
        self.bot.logger.error("Failed to fetch device from HomeAssistant", e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch device from HomeAssistant.", ephemeral=True)
      
      area_data: AreaModel | None = None
      if device_data.area_id is not None:
        try:
          area_data = self.bot.homeassistant_client.custom_get_area(area_id=device_data.area_id)
          if area_data is None:
            raise Exception("No area was returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch area from HomeAssistant", e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch area from HomeAssistant", ephemeral=True)

      escaped_device_id = self.bot.homeassistant_client.escape_id(device_data.id)
      history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "history"), device_id=escaped_device_id)
      logbook_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "logbook"), device_id=escaped_device_id)
      config_url = urllib.parse.urljoin(self.bot.homeassistant_url, f"config/devices/device/{escaped_device_id}")

      embed = discord.Embed(
        title=str(device_data.name) + (f" ({device_data.name_by_user})" if device_data.name_by_user is not None else ''),
        description=str(device_data.id),
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      if area_data is not None:
        embed.add_field(name='Area', value=f'**{area_data.name}** ({area_data.id})')
      else:
        embed.add_field(name='Area', value='-')

      embed.add_field(
        name='Other data',
        value="\n".join([
          f'**{key}**: {value}'
          for key, value in ({
            'menufacturer': device_data.menufacturer,
            'model': device_data.model,
            'model_id': device_data.model_id,
            'serial_number': device_data.serial_number,
            'hw_version': device_data.hw_version,
            'sw_version': device_data.sw_version
          }).items()
          if value is not None
        ])
      )
      
      if len(device_data.entities) > 0:
        entities: List[str] = []
        try:
          entities_data: List[EntityModel] = self.bot.homeassistant_client.cache_custom_get_entities()
          if entities_data is None:
            raise Exception("No entities were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch entities from HomeAssistant", e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch entities from HomeAssistant", ephemeral=True)

        for entity_id in device_data.entities:
          entity: EntityModel | None = find(lambda x: x.entity_id == entity_id, entities_data)
          if entity is not None:
            friendly_name = self.bot.homeassistant_client.get_entity_friendlyname(entity)
            entities.append(f"**{friendly_name if friendly_name is not None else "?"}** ({entity.entity_id})")
          else:
            entities.append(str(entity_id))
        embed.add_field(name="Entities", value=shorten_embed_value("\n".join(entities)))

      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Device history", url=history_url))
      view.add_item(discord.ui.Button(label="Device logbook", url=logbook_url))
      view.add_item(discord.ui.Button(label="Device config", url=config_url))
      
      await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
      self.bot.logger.error("General error", e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Devices(bot))