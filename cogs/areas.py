import urllib.parse
import datetime
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from enums.emojis import Emoji
from helpers import add_param, find, shorten_embed_value
from autocompletes import require_permission_autocomplete, area_autocomplete
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from models.EntityModel import EntityModel

class Areas(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

  @app_commands.command(
    name="get_area",
    description="Retrieves information about an area from Home Assistant"
  )
  @app_commands.describe(area_id="HomeAssistant area identifier")
  @app_commands.allowed_installs(guilds=True, users=True)
  @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
  @app_commands.autocomplete(area_id=require_permission_autocomplete(area_autocomplete, check_role=True))
  async def get_area(self, interaction: discord.Interaction, area_id: str):
    if not await self.bot.check_user_guild(interaction, check_role=True):
      return
    
    try:
      await interaction.response.defer(thinking=True)

      try:
        area_data: AreaModel | None = await self.bot.homeassistant_client.async_custom_get_area(area_id=area_id)
        if area_data is None:
          return await interaction.followup.send(f"{Emoji.ERROR} No area found.", ephemeral=True)
      except Exception as e:
        self.bot.logger.error("Failed to fetch area from HomeAssistant - %s %s", type(e), e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch area from HomeAssistant.", ephemeral=True)

      escaped_area_id = self.bot.homeassistant_client.escape_id(area_data.id)
      history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "history"), area_id=escaped_area_id)
      logbook_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "logbook"), area_id=escaped_area_id)
      config_url = urllib.parse.urljoin(self.bot.homeassistant_url, f"config/areas/area/{escaped_area_id}")
      
      embed = discord.Embed(
        title=str(area_data.name),
        description=str(area_data.id),
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      if len(area_data.devices) > 0:
        devices: List[str] = []
        try:
          devices_data: List[DeviceModel] = await self.bot.homeassistant_client.cache_async_custom_get_devices()
          if devices_data is None:
            raise Exception("No devices were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch devices from HomeAssistant - %s %s", type(e), e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch devices from HomeAssistant.", ephemeral=True)
        
        for device_id in area_data.devices:
          device: DeviceModel | None = find(lambda x: x.id == device_id, devices_data)
          if device is not None:
            devices.append(f"**{device.name}** ({device.id})")
          else:
            devices.append(str(device_id))

        embed.add_field(name="Devices", value=shorten_embed_value("\n".join(devices)))

      if len(area_data.entities) > 0:
        entities: List[str] = []
        try:
          entities_data: List[EntityModel] = await self.bot.homeassistant_client.cache_async_custom_get_entities()
          if entities_data is None:
            raise Exception("No entities were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch entities from HomeAssistant - %s %s", type(e), e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch entities from HomeAssistant", ephemeral=True)

        for entity_id in area_data.entities:
          entity: EntityModel | None = find(lambda x: x.entity_id == entity_id, entities_data)
          if entity is not None:
            friendly_name = self.bot.homeassistant_client.get_entity_friendlyname(entity)
            entities.append(f"**{friendly_name if friendly_name is not None else "?"}** ({entity.entity_id})")
          else:
            entities.append(str(entity_id))
        embed.add_field(name="Entities", value=shorten_embed_value("\n".join(entities)))

      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Area history", url=history_url))
      view.add_item(discord.ui.Button(label="Area logbook", url=logbook_url))
      view.add_item(discord.ui.Button(label="Area config", url=config_url))
      
      await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
      self.bot.logger.error("General error - %s %s", type(e), e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Areas(bot))