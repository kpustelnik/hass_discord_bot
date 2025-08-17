import discord
from discord import app_commands
from typing import List, Optional, Set
from bot import HASSDiscordBot

from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name, get_domain_from_entity_id, is_matching
from models.FloorModel import FloorModel
from models.AreaModel import AreaModel
from models.DeviceModel import DeviceModel
from models.EntityModel import EntityModel
from models.LabelModel import LabelModel
from models.ServiceModel import ServiceFieldSelectorEntityFilter, ServiceFieldSelectorDeviceFilter
from models.MDIIconMeta import MDIIconMeta
from enums.emojis import Emoji

# MDI Icons
async def get_icon_autocomplete_choices(
  bot: HASSDiscordBot,
  current_input: str
) -> List[app_commands.Choice[str]]:
  try:
    mdi_icons: List[MDIIconMeta] = bot.homeassistant_client.cache_get_mdi_icons()
    if mdi_icons is None:
      raise Exception("No icons were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch icons", e)
    return []
  
  target_tokens = tokenize(current_input)
  choice_list = [
    (
      max([
        fuzzy_keyword_match_with_order(tokenize(mdi_icon.name), target_tokens),
        *[
          fuzzy_keyword_match_with_order(tokenize(alias), target_tokens)
          for alias in mdi_icon.aliases
        ]
      ]),
      app_commands.Choice(
        name=shorten_option_name(f"{mdi_icon.name} ({mdi_icon.id})"),
        value=f"mdi:{mdi_icon.name}"
      )
    )
    for mdi_icon in mdi_icons
  ]
  return choice_list
  
async def icon_autocomplete(
  interaction: discord.Interaction,
  current_input: str
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_icon_autocomplete_choices(bot, current_input)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Labels
async def get_label_autocomplete_choices(
  bot: HASSDiscordBot,
  current_input: str,
  prefix: str = '',
  display_prefix: str = '',
  matching_labels: Optional[Set[str]] = None
) -> List[app_commands.Choice[str]]:
  try:
    homeassistant_labels: List[LabelModel] = bot.homeassistant_client.cache_custom_get_labels()
    if homeassistant_labels is None:
      raise Exception("No labels were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch labels", e)
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
        value=f'{prefix}{bot.homeassistant_client.escape_id(label.id)}'
      )
    )
    for label in checked_labels
  ]
  return choice_list
  
async def label_autocomplete(
  interaction: discord.Interaction,
  current_input: str
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_label_autocomplete_choices(bot, current_input)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Floors
async def get_floor_autocomplete_choices(
    bot: HASSDiscordBot,
    current_input: str,
    prefix: str = '',
    display_prefix: str = '',
    matching_floors: Optional[Set[str]] = None
) -> List[app_commands.Choice[str]]:
  try:
    homeassistant_floors: List[FloorModel] = bot.homeassistant_client.cache_custom_get_floors()
    if homeassistant_floors is None:
      raise Exception("No floors were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch floors", e)
    return []
  
  checked_floors = filter(lambda x: x.id in matching_floors, homeassistant_floors) if matching_floors is not None else homeassistant_floors

  target_tokens = tokenize(current_input)
  choice_list = [
    (
      max(
        fuzzy_keyword_match_with_order(tokenize(floor.id), target_tokens),
        fuzzy_keyword_match_with_order(tokenize(floor.name), target_tokens)
      ),
      app_commands.Choice(
        name=shorten_option_name(f"{display_prefix}{floor.name} ({floor.id})"),
        value=f'{prefix}{bot.homeassistant_client.escape_id(floor.id)}'
      )
    )
    for floor in checked_floors
  ]
  return choice_list
  
async def floor_autocomplete(
    interaction: discord.Interaction,
    current_input: str
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_floor_autocomplete_choices(bot, current_input)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Areas
async def get_area_autocomplete_choices(
  bot: HASSDiscordBot,
  current_input: str,
  prefix: str = '',
  display_prefix: str = '',
  matching_areas: Optional[Set[str]] = None,
) -> List[app_commands.Choice[str]]:
  try:
    homeassistant_areas: List[AreaModel] = bot.homeassistant_client.cache_custom_get_areas()
    if homeassistant_areas is None:
      raise Exception("No areas were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch areas", e)
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
        value=f'{prefix}{bot.homeassistant_client.escape_id(area.id)}'
      )
    )
    for area in checked_areas
  ]
  return choice_list
  
async def area_autocomplete(
  interaction: discord.Interaction,
  current_input: str
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_area_autocomplete_choices(bot, current_input)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Devices
async def get_device_autocomplete_choices(
  bot: HASSDiscordBot,
  current_input: str,
  prefix: str = '',
  display_prefix: str = '',
  matching_devices: Optional[Set[str]] = None,
  integration: Optional[str] = None,
  domain: Optional[str] = None
) -> List[app_commands.Choice[str]]:
  try:
    homeassistant_devices: List[DeviceModel] = bot.homeassistant_client.cache_custom_get_devices()
    if homeassistant_devices is None:
      raise Exception("No devices were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch devices", e)
    return []
    
  checked_devices = filter(lambda x: x.id in matching_devices, homeassistant_devices) if matching_devices is not None else homeassistant_devices
  
  # Filter entities not belonging to specified integration
  if integration is not None:
    try:
      integration_entities: Set[str] = set(bot.homeassistant_client.custom_get_integration_entities(integration))
    except Exception as e:
      bot.logger.error("Failed to fetch integration entities", type(e), e)
      return []
    checked_devices = filter(lambda x: integration_entities.intersection(set(x.entities)), checked_devices)

  # Filter entities not belonging to specified domain    
  if domain is not None:
    checked_devices = filter(lambda x: any(get_domain_from_entity_id(entity_id) == domain for entity_id in x.entities), checked_devices)

  target_tokens = tokenize(current_input)
  choice_list = [
    (
      max(
        fuzzy_keyword_match_with_order(tokenize(device.id), target_tokens),
        fuzzy_keyword_match_with_order(tokenize(device.name), target_tokens)
      ),
      app_commands.Choice(
        name=shorten_option_name(f"{display_prefix}{device.name} ({device.id})"),
        value=f'{prefix}{bot.homeassistant_client.escape_id(device.id)}'
      )
    )
    for device in checked_devices
  ]
  return choice_list
  
async def device_autocomplete(
  interaction: discord.Interaction,
  current_input: str
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_device_autocomplete_choices(bot, current_input)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]
  
async def filtered_device_autocomplete(
  interaction: discord.Interaction,
  current_input: str,
  integration: Optional[str] = None,
  domain: Optional[str] = None
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_device_autocomplete_choices(bot, current_input, integration=integration, domain=domain)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Entities
async def get_entity_autocomplete_choices(
  bot: HASSDiscordBot,
  current_input: str,
  prefix: str = '',
  display_prefix: str = '',
  matching_entities: Optional[Set[str]] = None,
  integration: Optional[str] = None,
  domain: Optional[str] = None
) -> List[app_commands.Choice[str]]:
  try:
    homeassistant_entities: List[EntityModel] = bot.homeassistant_client.cache_custom_get_entities()
    if homeassistant_entities is None:
      raise Exception("No entities were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch entities", e)
    return []
  
  checked_entities = filter(lambda x: x.entity_id in matching_entities, homeassistant_entities) if matching_entities is not None else homeassistant_entities
  
  # Filter entities not belonging to specified integration
  if integration is not None:
    try:
      integration_entities: List[str] = bot.homeassistant_client.custom_get_integration_entities(integration)
    except Exception as e:
      bot.logger.error("Failed to fetch integration entities", type(e), e)
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
        fuzzy_keyword_match_with_order(tokenize(friendly_name), target_tokens) if (friendly_name := bot.homeassistant_client.get_entity_friendlyname(entity)) is not None else 0
      ),
      app_commands.Choice(
        name=shorten_option_name(f"{display_prefix}{friendly_name if friendly_name is not None else "?"} ({entity.entity_id})"),
        value=f'{prefix}{bot.homeassistant_client.escape_id(entity.entity_id)}'
      )
    )
    for entity in checked_entities
  ]
  return choice_list

async def entity_autocomplete(
  interaction: discord.Interaction,
  current_input: str
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_entity_autocomplete_choices(bot, current_input)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

async def filtered_entity_autocomplete(
  interaction: discord.Interaction,
  current_input: str,
  integration: Optional[str] = None,
  domain: Optional[str] = None
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  choice_list: List[app_commands.Choice[str]] = await get_entity_autocomplete_choices(bot, current_input, integration=integration, domain=domain)
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Combined
async def label_floor_area_device_entity_autocomplete(
  interaction: discord.Interaction,
  current_input: str,
  domain: Optional[List[str]] = None,
  supported_features: Optional[List[int] | int] = None,
  integration: Optional[str] = None
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
  # Get matches
  matching_entities: Set[str] | None = get_matching_entities(bot, domain=domain, supported_features=supported_features, integration=integration)
  matching_devices: Set[str] | None = get_matching_devices(bot, matching_entities=matching_entities)
  matching_areas: Set[str] | None = get_matching_areas(bot, matching_entities=matching_entities, matching_devices=matching_devices)
  matching_floors: Set[str] | None = get_matching_floors(bot, matching_entities=matching_entities, matching_areas=matching_areas)
  matching_labels: Set[str] | None = get_matching_labels(bot, matching_entities=matching_entities, matching_devices=matching_devices, matching_areas=matching_areas)

  # Create all choices
  label_choice_list = await get_label_autocomplete_choices(bot, current_input, prefix='LABEL$', display_prefix='Label: ', matching_labels=matching_labels)
  floor_choice_list = await get_floor_autocomplete_choices(bot, current_input, prefix='FLOOR$', display_prefix='Floor: ', matching_floors=matching_floors)
  area_choice_list = await get_area_autocomplete_choices(bot, current_input, prefix='AREA$', display_prefix='Area: ', matching_areas=matching_areas)
  device_choice_list = await get_device_autocomplete_choices(bot, current_input, prefix='DEVICE$', display_prefix='Device: ', matching_devices=matching_devices)
  entity_choice_list = await get_entity_autocomplete_choices(bot, current_input, prefix='ENTITY$', display_prefix='Entity: ', matching_entities=matching_entities)
  choice_list = area_choice_list + device_choice_list + entity_choice_list + floor_choice_list + label_choice_list
  choice_list.sort(key=lambda x: x[0], reverse=True)

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

# Custom
async def choice_autocomplete(
  interaction: discord.Interaction,
  current_input: str,
  all_choices: List[str]
) -> List[app_commands.Choice[str]]:
  bot: HASSDiscordBot = interaction.client
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

  min_score = choice_list[0][0] * (1 - bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
  return [x[1] for x in choice_list[:bot.MAX_AUTOCOMPLETE_CHOICES] if x[0] >= min_score]

def require_permission_autocomplete(
  func, check_role: Optional[str] = None
) -> List[app_commands.Choice[str]]:
  async def handler(interaction: discord.Interaction, current_input: str) -> List[app_commands.Choice[str]]:
    bot: HASSDiscordBot = interaction.client
    if not await bot.check_user_guild(interaction, check_role):
      return [app_commands.Choice(name=f'{Emoji.WARNING} Failed to fetch suggestions.', value='')]
    
    return await func(interaction, current_input)
  return handler

# Validation
def require_choice(input: str, all_choices: List[str]) -> str:
  if input in all_choices:
    return input
  else:
    raise Exception("Incorrect choice")
  
# Labels, floors, area, devices, entities matching
def get_matching_labels(
  bot: HASSDiscordBot,
  matching_entities: Optional[Set[str]],
  matching_devices: Optional[Set[str]],
  matching_areas: Optional[Set[str]]
) -> Set[str] | None:
  if matching_entities is None and matching_devices is None and matching_areas is None:
    return None
  
  try:
    homeassistant_labels: List[LabelModel] = bot.homeassistant_client.cache_custom_get_labels()
    if homeassistant_labels is None:
      raise Exception("No labels were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch labels", e)
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

def get_matching_floors(
    bot: HASSDiscordBot,
    matching_entities: Optional[Set[str]],
    matching_areas: Optional[Set[str]]
) -> Set[str] | None:
  if matching_entities is None and matching_areas is None:
    return None
  
  try:
    homeassistant_floors: List[FloorModel] = bot.homeassistant_client.cache_custom_get_floors()
    if homeassistant_floors is None:
      raise Exception("No floors were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch floors", e)
    return []
  
  matching_floors = set()
  for floor in homeassistant_floors:
    if matching_areas is not None and len(set(floor.areas).intersection(matching_areas)) != 0:
      matching_floors.add(floor.id)
    elif matching_entities is not None and len(set(floor.entities).intersection(matching_entities)) != 0:
      matching_floors.add(floor.id)

  return matching_floors

def get_matching_areas(
    bot: HASSDiscordBot,
    matching_entities: Optional[Set[str]],
    matching_devices: Optional[Set[str]]
) -> Set[str] | None:
  if matching_entities is None and matching_devices is None:
    return None
  
  try:
    homeassistant_areas: List[AreaModel] = bot.homeassistant_client.cache_custom_get_areas()
    if homeassistant_areas is None:
      raise Exception("No areas were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch areas", e)
    return []
  
  matching_areas = set()
  for area in homeassistant_areas:
    if matching_devices is not None and len(set(area.devices).intersection(matching_devices)) != 0:
      matching_areas.add(area.id)
    elif matching_entities is not None and len(set(area.entities).intersection(matching_entities)) != 0:
      matching_areas.add(area.id)
  
  return matching_areas


def get_matching_devices(
  bot: HASSDiscordBot,
  matching_entities: Optional[Set[str]],
  device_filter: Optional[List[ServiceFieldSelectorDeviceFilter]] = None
) -> Set[str] | None:
  if matching_entities is None and (device_filter is None or len(device_filter) == 0):
    return None
  
  try:
    homeassistant_devices: List[DeviceModel] = bot.homeassistant_client.cache_custom_get_devices()
    if homeassistant_devices is None:
      raise Exception("No devices were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch devices", e)
    return set()
  
  if matching_entities is not None:
    homeassistant_devices = filter(lambda x: len(set(x.entities).intersection(matching_entities)) != 0, homeassistant_devices)
  
  if not (device_filter is None or len(device_filter) == 0):
    filter_matching_devices: Set[DeviceModel] = set()
    for current_filter in device_filter:
      filter_devices: List[DeviceModel] = homeassistant_devices
      if current_filter.integration is not None:
        try:
          integration_entities: Set[str] = set(bot.homeassistant_client.custom_get_integration_entities(current_filter.integration))
        except Exception as e:
          bot.logger.error("Failed to fetch integration entities", type(e), e)
          return set()
        # I don't think it's currently possible to fetch the device's config entry and it's related integration?
        filter_devices = filter(lambda x: len(integration_entities.intersection(set(x.entities))) != 0, filter_devices) # Any of the device's entities should belong to the integration

      if current_filter.manufacturer is not None:
        filter_devices = filter(lambda x: x.manufacturer is not None and x.manufacturer == current_filter.manufacturer, filter_devices)

      if current_filter.model is not None:
        filter_devices = filter(lambda x: x.model is not None and x.model == current_filter.model, filter_devices)

      if current_filter.model_id is not None:
        filter_devices = filter(lambda x: x.model_id is not None and x.model_id == current_filter.model_id, filter_devices)

      filter_matching_devices.update(filter_devices)
    homeassistant_devices = list(filter_matching_devices)

  return set([ device.id for device in homeassistant_devices ])  

def get_matching_entities(
    bot: HASSDiscordBot,
    entity_filter: Optional[List[ServiceFieldSelectorEntityFilter]] = None
) -> Set[str] | None:
  if entity_filter is None or len(entity_filter) == 0:
    return None # Function returns None if there is no filter
  
  try:
    homeassistant_entities: List[EntityModel] = bot.homeassistant_client.cache_custom_get_entities()
    if homeassistant_entities is None:
      raise Exception("No entities were returned")
  except Exception as e:
    bot.logger.error("Failed to fetch entities", type(e), e)
    return set()
  
  filter_matching_entities: Set[str] = set()
  for current_filter in entity_filter:
    filter_entities: List[EntityModel] = homeassistant_entities
    if current_filter.integration is not None:
      try:
        integration_entities: Set[str] = set(bot.homeassistant_client.custom_get_integration_entities(current_filter.integration))
      except Exception as e:
        bot.logger.error("Failed to fetch integration entities", type(e), e)
        return set()
      filter_entities = filter(lambda x: x.entity_id in integration_entities, filter_entities)
    
    if current_filter.domain is not None: # Remove entities which have incorrect domain
      filter_entities = filter(lambda x: is_matching(current_filter.domain, get_domain_from_entity_id(x.entity_id)), filter_entities)

    if current_filter.device_class is not None: # Remove entities which have incorrect device_class (or don't have it)
      filter_entities = filter(lambda x: (device_class := x.attributes.get('device_class') is not None and is_matching(current_filter.device_class, device_class)), filter_entities)
    
    if current_filter.supported_features is not None: # Remove entities which don't have required features
      new_filter_entities: List[EntityModel] = []
      for entity in filter_entities:
        entity_supported_features = entity.attributes.get('supported_features')
        if entity_supported_features is not None and isinstance(entity_supported_features, int):
          any_matching = False
          if isinstance(current_filter.supported_features, int):
            any_matching = current_filter.supported_features & entity_supported_features != 0
          elif isinstance(current_filter.supported_features, list):
            for feature in current_filter.supported_features:
              if feature & entity_supported_features != 0:
                any_matching = True
                break
          
          if any_matching:
            new_filter_entities.append(entity)
      filter_entities = new_filter_entities

    filter_matching_entities.update([ x.entity_id for x in filter_entities ])

  return filter_matching_entities
