import discord
from discord import app_commands
from typing import List

from bot import HASSDiscordBot
from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from models.EntityModel import EntityModel

class Autocompletes():
  async def area_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_areas: List[AreaModel] = cog.bot.homeassistant_client.cache_custom_get_areas()
      if homeassistant_areas is None:
        raise Exception("No areas were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch areas", e)
      return []
      
    target_tokens = tokenize(current_input)
    choice_list = [
      (
        max(
          fuzzy_keyword_match_with_order(tokenize(area.id), target_tokens),
          fuzzy_keyword_match_with_order(tokenize(area.name), target_tokens)
        ),
        app_commands.Choice(
          name=shorten_option_name(f"{area.name} ({area.id})"),
          value=area.id
        )
      )
      for area in homeassistant_areas
    ]
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  async def device_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_devices: List[DeviceModel] = cog.bot.homeassistant_client.cache_custom_get_devices()
      if homeassistant_devices is None:
        raise Exception("No devices were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch devices", e)
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

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

  async def entity_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_entities: List[EntityModel] = cog.bot.homeassistant_client.cache_custom_get_entities()
      if homeassistant_entities is None:
        raise Exception("No entities were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch entities", e)
      return []
      
    target_tokens = tokenize(current_input)
    choice_list = [
      (
        max(
          fuzzy_keyword_match_with_order(tokenize(entity.entity_id), target_tokens),
          fuzzy_keyword_match_with_order(tokenize(friendly_name), target_tokens) if (friendly_name := cog.bot.homeassistant_client.get_entity_friendlyname(entity)) is not None else 0
        ),
        app_commands.Choice(
          name=shorten_option_name(f"{friendly_name if friendly_name is not None else "?"} ({entity.entity_id})"),
          value=entity.entity_id
        )
      )
      for entity in homeassistant_entities
    ]
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]