import urllib.parse
import datetime
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from helpers import add_param, find
from autocompletes import entity_autocomplete, require_permission_autocomplete
from models.EntityModel import EntityModel
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from enums.emojis import Emoji

class Entities(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot
    self.OMMITED_ENTITY_ATTRIBUTES = ["friendly_name"]

  @app_commands.command(
    name="get_entity",
    description="Retrieves information about an entity from Home Assistant"
  )
  @app_commands.describe(entity_id="HomeAssistant entity identifier")
  @app_commands.allowed_installs(guilds=True, users=True)
  @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
  @app_commands.autocomplete(entity_id=require_permission_autocomplete(entity_autocomplete, check_role=True))
  async def get_entity(self, interaction: discord.Interaction, entity_id: str):
    if not await self.bot.check_user_guild(interaction, check_role=True):
      return

    try:
      await interaction.response.defer(thinking=True)

      try:
        entity_data: EntityModel | None = await self.bot.homeassistant_client.async_custom_get_entity(entity_id=entity_id)
        if entity_data is None:
          return await interaction.followup.send(f"{Emoji.ERROR} No entity found.", ephemeral=True)
      except Exception as e:
        self.bot.logger.error("Failed to fetch entity from HomeAssistant - %s %s", type(e), e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch entity from HomeAssistant.", ephemeral=True)
      
      try:
        areas_data: List[AreaModel] = await self.bot.homeassistant_client.cache_async_custom_get_areas()
        if areas_data is None:
          raise Exception("No areas were returned")
      except Exception as e:
        self.bot.logger.error("Failed to fetch areas from HomeAssistant - %s %s", type(e), e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch areas from HomeAssistant", ephemeral=True)
      
      try:
        devices_data: List[DeviceModel] = await self.bot.homeassistant_client.cache_async_custom_get_devices()
        if devices_data is None:
          raise Exception("No devices were returned")
      except Exception as e:
        self.bot.logger.error("Failed to fetch devices from HomeAssistant - %s %s", type(e), e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch devices from HomeAssistant", ephemeral=True)

      escaped_entity_id = self.bot.homeassistant_client.escape_id(entity_data.entity_id)
      friendly_name = self.bot.homeassistant_client.get_entity_friendlyname(entity_data)
      history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "history"), entity_id=escaped_entity_id)
      logbook_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "logbook"), entity_id=escaped_entity_id)

      embed = discord.Embed(
        title=f"{friendly_name if friendly_name is not None else "?"}",
        description=str(entity_data.entity_id),
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      embed.add_field(name="State", value=str(entity_data.state))

      # Area & Device
      device_data: DeviceModel | None = find(lambda device: entity_data.entity_id in device.entities, devices_data)
      area_data: AreaModel | None = find(lambda area: entity_data.entity_id in area.entities, areas_data)
      if area_data is None and device_data is not None:
        area_data = find(lambda area: area.id == device_data.area_id, areas_data)

      # Add to embed
      if device_data is not None:
        embed.add_field(name="Device", value=f"**{device_data.name}** ({device_data.id})")
      else:
        embed.add_field(name="Device", value="-")

      if area_data is not None:
        embed.add_field(name="Area", value=f"**{area_data.name}** ({area_data.id})")
      else:
        embed.add_field(name="Area", value="-")

      embed.add_field(name="Last changed", value=str(entity_data.last_changed))
      embed.add_field(name="Last updated", value=str(entity_data.last_updated))
      embed.add_field(name="Last reported", value=str(entity_data.last_reported))
      embed.add_field(name="", value="Attributes", inline=False)
      for name, value in filter(lambda x: x[0] not in self.OMMITED_ENTITY_ATTRIBUTES, entity_data.attributes.items()):
        embed.add_field(name=name, value=str(value))

      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Entity history", url=history_url))
      view.add_item(discord.ui.Button(label="Entity logbook", url=logbook_url))

      await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
      self.bot.logger.error("General error - %s %s", type(e), e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)


async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Entities(bot))