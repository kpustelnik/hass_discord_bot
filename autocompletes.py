import discord
from discord import app_commands
from typing import List, Optional, Set

from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name, get_domain_from_entity_id
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from models.EntityModel import EntityModel
from models.LabelModel import LabelModel

class Autocompletes():
  # Labels
  async def get_label_autocomplete_choices(
      cog,
      current_input: str,
      prefix: str = '',
      display_prefix: str = '',
      matching_labels: Set[str] | None = None
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_labels: List[LabelModel] = cog.bot.homeassistant_client.cache_custom_get_labels()
      if homeassistant_labels is None:
        raise Exception("No labels were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch labels", e)
      return []
      
    checked_labels = filter(lambda x: x.id in matching_labels, homeassistant_labels) if matching_labels is not None else homeassistant_labels
      
    target_tokens = tokenize(current_input)
    choice_list = [
      (
        max(
          fuzzy_keyword_match_with_order(tokenize(label.id), target_tokens),
          fuzzy_keyword_match_with_order(tokenize(label.name), target_tokens)
        ),
        app_commands.Choice(
          name=shorten_option_name(f"{display_prefix}{label.name} ({label.id})"),
          value=f'{prefix}{cog.bot.homeassistant_client.escape_id(label.id)}'
        )
      )
      for label in checked_labels
    ]
    return choice_list
    
  async def label_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    choice_list: List[app_commands.Choice[str]] = await Autocompletes.get_label_autocomplete_choices(cog, current_input)
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  # Areas
  async def get_area_autocomplete_choices(
      cog,
      current_input: str,
      prefix: str = '',
      display_prefix: str = '',
      matching_areas: Set[str] | None = None
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_areas: List[AreaModel] = cog.bot.homeassistant_client.cache_custom_get_areas()
      if homeassistant_areas is None:
        raise Exception("No areas were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch areas", e)
      return []
      
    checked_areas = filter(lambda x: x.id in matching_areas, homeassistant_areas) if matching_areas is not None else homeassistant_areas
      
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
      for area in checked_areas
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
      display_prefix: str = '',
      matching_devices: Set[str] | None = None
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_devices: List[DeviceModel] = cog.bot.homeassistant_client.cache_custom_get_devices()
      if homeassistant_devices is None:
        raise Exception("No devices were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch devices", e)
      return []
      
    checked_devices = filter(lambda x: x.id in matching_devices, homeassistant_devices) if matching_devices is not None else homeassistant_devices

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
      for device in checked_devices
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
      display_prefix: str = '',
      matching_entities: Set[str] | None = None,
      integration: Optional[str] = None,
      domain: Optional[str] = None
  ) -> List[app_commands.Choice[str]]:
    try:
      homeassistant_entities: List[EntityModel] = cog.bot.homeassistant_client.cache_custom_get_entities()
      if homeassistant_entities is None:
        raise Exception("No entities were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch entities", e)
      return []
    
    checked_entities = filter(lambda x: x.entity_id in matching_entities, homeassistant_entities) if matching_entities is not None else homeassistant_entities
    
    # Filter entities not belonging to specified integration
    if integration is not None:
      try:
        integration_entities: List[str] = cog.bot.homeassistant_client.custom_get_integration_entities(integration)
      except Exception as e:
        cog.bot.logger.error("Failed to fetch integration entities", type(e), e)
        return []
      checked_entities = filter(lambda x: x.entity_id in integration_entities, checked_entities)

    # Filter entities not belonging to specified domain    
    if domain is not None:
      checked_entities = filter(lambda x: get_domain_from_entity_id(x.entity_id) == domain, checked_entities)

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
      for entity in checked_entities
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
  
  async def filtered_entity_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str,
      integration: Optional[str] = None,
      domain: Optional[str] = None
  ) -> List[app_commands.Choice[str]]:
    choice_list: List[app_commands.Choice[str]] = await Autocompletes.get_entity_autocomplete_choices(cog, current_input, integration=integration, domain=domain)
    choice_list.sort(key=lambda x: x[0], reverse=True)

    min_score = choice_list[0][0] * (1 - cog.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:cog.bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
  # Combined
  async def label_area_device_entity_autocomplete(
      cog,
      interaction: discord.Interaction,
      current_input: str,
      domain: Optional[List[str]] = None,
      supported_features: Optional[List[int] | int] = None,
      integration: Optional[str] = None
  ) -> List[app_commands.Choice[str]]:
    # Get matches
    matching_entities: Set[str] | None = Autocompletes.get_matching_entities(cog, domain=domain, supported_features=supported_features, integration=integration)
    matching_devices: Set[str] | None = Autocompletes.get_matching_devices(cog, matching_entities=matching_entities)
    matching_areas: Set[str] | None = Autocompletes.get_matching_areas(cog, matching_entities=matching_entities, matching_devices=matching_devices)
    matching_labels: Set[str] | None = Autocompletes.get_matching_labels(cog, matching_entities=matching_entities, matching_devices=matching_devices, matching_areas=matching_areas)

    # Create all choices
    label_choice_list = await Autocompletes.get_label_autocomplete_choices(cog, current_input, prefix='LABEL$', display_prefix='Label: ', matching_labels=matching_labels)
    area_choice_list = await Autocompletes.get_area_autocomplete_choices(cog, current_input, prefix='AREA$', display_prefix='Area: ', matching_areas=matching_areas)
    device_choice_list = await Autocompletes.get_device_autocomplete_choices(cog, current_input, prefix='DEVICE$', display_prefix='Device: ', matching_devices=matching_devices)
    entity_choice_list = await Autocompletes.get_entity_autocomplete_choices(cog, current_input, prefix='ENTITY$', display_prefix='Entity: ', matching_entities=matching_entities)
    choice_list = area_choice_list + device_choice_list + entity_choice_list + label_choice_list
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
  
  # Validation
  @staticmethod
  def require_choice(input: str, all_choices: List[str]) -> str:
    if input in all_choices:
      return input
    else:
      raise Exception("Incorrect choice")
    
  # Labels, area, devices, entities matching
  def get_matching_labels(
      cog,
      matching_entities: Set[str] | None,
      matching_devices: Set[str] | None,
      matching_areas: Set[str] | None
  ) -> Set[str] | None:
    if matching_entities is None and matching_devices is None and matching_areas is None:
      return None
    
    try:
      homeassistant_labels: List[LabelModel] = cog.bot.homeassistant_client.cache_custom_get_labels()
      if homeassistant_labels is None:
        raise Exception("No labels were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch labels", e)
      return []
    
    matching_labels = set()
    for label in homeassistant_labels:
      if matching_areas is not None and len(set(label.areas).intersection(matching_areas)) != 0:
        matching_labels.add(label.id)
      elif matching_devices is not None and len(set(label.devices).intersection(matching_devices)) != 0:
        matching_labels.add(label.id)
      elif matching_entities is not None and len(set(label.entities).intersection(matching_entities)) != 0:
        matching_labels.add(label.id)
    
    return matching_labels

  def get_matching_areas(
      cog,
      matching_entities: Set[str] | None,
      matching_devices: Set[str] | None
  ) -> Set[str] | None:
    if matching_entities is None and matching_devices is None:
      return None
    
    try:
      homeassistant_areas: List[AreaModel] = cog.bot.homeassistant_client.cache_custom_get_areas()
      if homeassistant_areas is None:
        raise Exception("No areas were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch areas", e)
      return []
    
    matching_areas = set()
    for area in homeassistant_areas:
      if matching_devices is not None and len(set(area.devices).intersection(matching_devices)) != 0:
        matching_areas.add(area.id)
      elif matching_entities is not None and len(set(area.entities).intersection(matching_entities)) != 0:
        matching_areas.add(area.id)
    
    return matching_areas
  

  def get_matching_devices(
      cog,
      matching_entities: Set[str] | None
  ) -> Set[str] | None:
    if matching_entities is None:
      return None
    
    try:
      homeassistant_devices: List[DeviceModel] = cog.bot.homeassistant_client.cache_custom_get_devices()
      if homeassistant_devices is None:
        raise Exception("No devices were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch devices", e)
      return []
    
    return set([
      device.id
      for device in filter(lambda x: len(set(x.entities).intersection(matching_entities)) != 0, homeassistant_devices)
    ])
    

  def get_matching_entities(
      cog,
      domain: Optional[List[str]] = None,
      supported_features: Optional[List[int] | int] = None,
      integration: Optional[str] = None
  ) -> Set[str] | None:
    if domain is None and supported_features is None and integration is None:
      return None # Returns None if all entities are passing
    
    try:
      homeassistant_entities: List[EntityModel] = cog.bot.homeassistant_client.cache_custom_get_entities()
      if homeassistant_entities is None:
        raise Exception("No entities were returned")
    except Exception as e:
      cog.bot.logger.error("Failed to fetch entities", type(e), e)
      return []
    
    integration_entities: List[str] | None = None
    try:
      if integration is not None:
        integration_entities: List[str] = cog.bot.homeassistant_client.custom_get_integration_entities(integration)
    except Exception as e:
      cog.bot.logger.error("Failed to fetch integration entities", type(e), e)
      return []
    
    passing_entities: Set[str] = set()
    for entity in homeassistant_entities:
      entity_domain: str | None = get_domain_from_entity_id(entity_id=entity.entity_id)
      if domain is not None:
        if entity_domain is None or entity_domain not in domain:
          continue # Condition not matching, skip
      
      if supported_features is not None:
        entity_supported_features = entity.attributes.get('supported_features')
        if entity_supported_features is not None and isinstance(entity_supported_features, int):
          any_matching = False
          if isinstance(supported_features, int):
            any_matching = supported_features & entity_supported_features != 0
          elif isinstance(supported_features, list):
            for feature in supported_features:
              if feature & entity_supported_features != 0:
                any_matching = True
                break
          
          if not any_matching:
            continue # Required feature is not supported, skip
        else:
          continue # No supported features, skip
      
      if integration_entities is not None:
        if entity.entity_id not in integration_entities:
          continue # Entity not in integration, skip

      passing_entities.add(entity.entity_id)
    return passing_entities
