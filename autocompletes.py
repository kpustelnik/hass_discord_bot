import discord
from discord import app_commands
from typing import List

from bot import HASSDiscordBot
from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name

class Autocompletes():
  async def device_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_devices = cog.bot.homeassistant_client.cache_custom_get_devices()
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

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

  async def entity_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_entities = cog.bot.homeassistant_client.cache_get_entities()
      if homeassistant_entities is None:
        raise Exception("No entities were returned")
    except Exception as e:
      print("Failed to fetch entities", e)
      return []
      
    target_tokens = tokenize(current_input)
    choice_list = [
      (
        max(
          fuzzy_keyword_match_with_order(tokenize(entity.entity_id), target_tokens),
          fuzzy_keyword_match_with_order(tokenize(entity.state.attributes["friendly_name"]), target_tokens) if "friendly_name" in entity.state.attributes else 0
        ),
        app_commands.Choice(
          name=shorten_option_name(f"{entity.state.attributes["friendly_name"] if "friendly_name" in entity.state.attributes else "?"} ({entity.entity_id})"),
          value=entity.entity_id
        )
      )
      for group in homeassistant_entities.values()
      for id, entity in group.entities.items()
    ]
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]