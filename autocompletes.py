import discord
from discord import app_commands
from typing import List

from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from models.EntityModel import EntityModel

class Autocompletes():
  # Areas
  async def get_area_autocomplete_choices(
      cog,
      current_input: str,
      prefix: str = '',
      display_prefix: str = ''
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
          name=shorten_option_name(f"{display_prefix}{area.name} ({area.id})"),
          value=f'{prefix}{cog.bot.homeassistant_client.escape_id(area.id)}'
        )
      )
      for area in homeassistant_areas
    ]
    return choice_list
    
  async def area_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    choice_list: List[app_commands.Choice[str]] = await Autocompletes.get_area_autocomplete_choices(cog, current_input)
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  # Devices
  async def get_device_autocomplete_choices(
      cog,
      current_input: str,
      prefix: str = '',
      display_prefix: str = ''
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
          name=shorten_option_name(f"{display_prefix}{device.name} ({device.id})"),
          value=f'{prefix}{cog.bot.homeassistant_client.escape_id(device.id)}'
        )
      )
      for device in homeassistant_devices
    ]
    return choice_list
    
  async def device_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    choice_list: List[app_commands.Choice[str]] = await Autocompletes.get_device_autocomplete_choices(cog, current_input)
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  # Entities
  async def get_entity_autocomplete_choices(
      cog,
      current_input: str,
      prefix: str = '',
      display_prefix: str = ''
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
          name=shorten_option_name(f"{display_prefix}{friendly_name if friendly_name is not None else "?"} ({entity.entity_id})"),
          value=f'{prefix}{cog.bot.homeassistant_client.escape_id(entity.entity_id)}'
        )
      )
      for entity in homeassistant_entities
    ]
    return choice_list

  async def entity_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    choice_list: List[app_commands.Choice[str]] = await Autocompletes.get_entity_autocomplete_choices(cog, current_input)
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  # Combined
  async def area_device_entity_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    area_choice_list = await Autocompletes.get_area_autocomplete_choices(cog, current_input, prefix='AREA$', display_prefix='Area: ')
    device_choice_list = await Autocompletes.get_device_autocomplete_choices(cog, current_input, prefix='DEVICE$', display_prefix='Device: ')
    entity_choice_list = await Autocompletes.get_entity_autocomplete_choices(cog, current_input, prefix='ENTITY$', display_prefix='Entity: ')
    choice_list = area_choice_list + device_choice_list + entity_choice_list
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  # Custom
  async def choice_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str,
      all_choices: List[str]
  ) -> List[app_commands.Choice[str]]:
    target_tokens = tokenize(current_input)
    choice_list = [
      (
        fuzzy_keyword_match_with_order(tokenize(str(choice)), target_tokens),
        app_commands.Choice(
          name=shorten_option_name(str(choice)),
          value=str(choice)
        )
      )
      for choice in all_choices
    ]
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  def require_choice(input: str, all_choices: List[str]) -> str:
    if input in all_choices:
      return input
    else:
      raise Exception("Incorrect choice")