import urllib.parse
import datetime
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from enums.emojis import Emoji
from helpers import add_param, find, shorten_embed_value
from autocompletes import Autocompletes
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from models.EntityModel import EntityModel
from models.LabelModel import LabelModel

class Labels(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    self.bot.tree.add_command(
      app_commands.Command(
        name="get_label",
        description="Retrieves information about a label from Home Assistant",
        callback=self.get_label
      ), 
      guild=discord.Object(self.bot.discord_main_guild_id) if self.bot.discord_main_guild_id is not None else None) # Get label command

  @app_commands.autocomplete(label_id=Autocompletes.label_autocomplete)
  @app_commands.describe(label_id="HomeAssistant label identifier")
  async def get_label(self, interaction: discord.Interaction, label_id: str):
    if not await self.bot.check_user_role(interaction):
      return

    try:
      await interaction.response.defer()

      try:
        label_data: LabelModel | None = self.bot.homeassistant_client.custom_get_label(label_id=label_id)
        if label_data is None:
          return await interaction.followup.send(f"{Emoji.ERROR} No label found.", ephemeral=True)
      except Exception as e:
        self.bot.logger.error("Failed to fetch label from HomeAssistant", e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch label from HomeAssistant.", ephemeral=True)

      escaped_label_id = self.bot.homeassistant_client.escape_id(label_data.id)
      history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "history"), label_id=escaped_label_id)
      logbook_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "logbook"), label_id=escaped_label_id)
      
      embed = discord.Embed(
        title=str(label_data.name),
        description=str(label_data.id),
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      if label_data.description is not None:
        embed.add_field(name='Description', value=str(label_data.description))

      # Areas parsing
      if len(label_data.areas) > 0:
        areas: List[str] = []
        try:
          areas_data: List[AreaModel] = self.bot.homeassistant_client.cache_custom_get_areas()
          if areas_data is None:
            raise Exception("No areas were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch areas from HomeAssistant", e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch areas from HomeAssistant.", ephemeral=True)
        
        for area_id in label_data.areas:
          area: AreaModel | None = find(lambda x: x.id == area_id, areas_data)
          if area is not None:
            areas.append(f'**{area.name}** ({area.id})')
          else:
            areas.append(str(area_id))
        
        embed.add_field(name="Areas", value=shorten_embed_value("\n".join(areas)))

      # Devices parsing
      if len(label_data.devices) > 0:
        devices: List[str] = []
        try:
          devices_data: List[DeviceModel] = self.bot.homeassistant_client.cache_custom_get_devices()
          if devices_data is None:
            raise Exception("No devices were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch devices from HomeAssistant", e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch devices from HomeAssistant.", ephemeral=True)
        
        for device_id in label_data.devices:
          device: DeviceModel | None = find(lambda x: x.id == device_id, devices_data)
          if device is not None:
            devices.append(f"**{device.name}** ({device.id})")
          else:
            devices.append(str(device_id))

        embed.add_field(name="Devices", value=shorten_embed_value("\n".join(devices)))

      # Entities parsing
      if len(label_data.entities) > 0:
        entities: List[str] = []
        try:
          entities_data: List[EntityModel] = self.bot.homeassistant_client.cache_custom_get_entities()
          if entities_data is None:
            raise Exception("No entities were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch entities from HomeAssistant", e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch entities from HomeAssistant", ephemeral=True)

        for entity_id in label_data.entities:
          entity: EntityModel | None = find(lambda x: x.entity_id == entity_id, entities_data)
          if entity is not None:
            friendly_name = self.bot.homeassistant_client.get_entity_friendlyname(entity)
            entities.append(f"**{friendly_name if friendly_name is not None else "?"}** ({entity.entity_id})")
          else:
            entities.append(str(entity_id))
        embed.add_field(name="Entities", value=shorten_embed_value("\n".join(entities)))

      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Label history", url=history_url))
      view.add_item(discord.ui.Button(label="Label logbook", url=logbook_url))
      
      await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
      self.bot.logger.error("General error", e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Labels(bot))