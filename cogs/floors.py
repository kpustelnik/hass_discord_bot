import urllib.parse
import datetime
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from enums.emojis import Emoji
from helpers import add_param, find, shorten_embed_value
from autocompletes import require_permission_autocomplete, floor_autocomplete
from models.FloorModel import FloorModel
from models.AreaModel import AreaModel
from models.EntityModel import EntityModel

class Floors(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

  @app_commands.command(
    name="get_floor",
    description="Retrieves information about a floor from Home Assistant"
  )
  @app_commands.describe(floor_id="HomeAssistant floor identifier")
  @app_commands.allowed_installs(guilds=True, users=True)
  @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
  @app_commands.autocomplete(floor_id=require_permission_autocomplete(floor_autocomplete, check_role=True))
  async def get_floor(self, interaction: discord.Interaction, floor_id: str):
    if not await self.bot.check_user_guild(interaction, check_role=True):
      return
    
    try:
      await interaction.response.defer(thinking=True)

      try:
        floor_data: FloorModel | None = await self.bot.homeassistant_client.async_custom_get_floor(floor_id=floor_id)
        if floor_data is None:
          return await interaction.followup.send(f"{Emoji.ERROR} No floor found.", ephemeral=True)
      except Exception as e:
        self.bot.logger.error("Failed to fetch floor from HomeAssistant - %s %s", type(e), e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch floor from HomeAssistant.", ephemeral=True)

      escaped_floor_id = self.bot.homeassistant_client.escape_id(floor_data.id)
      history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "history"), floor_id=escaped_floor_id)
      logbook_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, "logbook"), floor_id=escaped_floor_id)
      
      embed = discord.Embed(
        title=str(floor_data.name),
        description=str(floor_data.id),
        color=discord.Colour.default(),
        timestamp=datetime.datetime.now()
      )

      if len(floor_data.areas) > 0:
        areas: List[str] = []
        try:
          areas_data: List[AreaModel] = await self.bot.homeassistant_client.cache_async_custom_get_areas()
          if areas_data is None:
            raise Exception("No areas were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch areas from HomeAssistant - %s %s", type(e), e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch areas from HomeAssistant.", ephemeral=True)
        
        for area_id in floor_data.areas:
          area: AreaModel | None = find(lambda x: x.id == area_id, areas_data)
          if area is not None:
            areas.append(f"**{area.name}** ({area.id})")
          else:
            areas.append(str(area_id))

        embed.add_field(name="Areas", value=shorten_embed_value("\n".join(areas)))

      if len(floor_data.entities) > 0:
        entities: List[str] = []
        try:
          entities_data: List[EntityModel] = await self.bot.homeassistant_client.cache_async_custom_get_entities()
          if entities_data is None:
            raise Exception("No entities were returned")
        except Exception as e:
          self.bot.logger.error("Failed to fetch entities from HomeAssistant - %s %s", type(e), e)
          return await interaction.followup.send(f"{Emoji.ERROR} Failed to fetch entities from HomeAssistant", ephemeral=True)

        for entity_id in floor_data.entities:
          entity: EntityModel | None = find(lambda x: x.entity_id == entity_id, entities_data)
          if entity is not None:
            friendly_name = self.bot.homeassistant_client.get_entity_friendlyname(entity)
            entities.append(f"**{friendly_name if friendly_name is not None else "?"}** ({entity.entity_id})")
          else:
            entities.append(str(entity_id))
        embed.add_field(name="Entities", value=shorten_embed_value("\n".join(entities)))

      view = discord.ui.View()
      view.add_item(discord.ui.Button(label="Floor history", url=history_url))
      view.add_item(discord.ui.Button(label="Floor logbook", url=logbook_url))
      
      await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
      self.bot.logger.error("General error - %s %s", type(e), e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Floors(bot))