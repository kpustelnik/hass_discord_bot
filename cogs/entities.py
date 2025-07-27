import urllib.parse
import datetime
from typing import List

import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from helpers import tokenize, fuzzy_keyword_match_with_order, shorten_option_name, add_param

from enums.homeassistant_cache_id import homeassistant_cache_id

class Entities(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot
    self.OMMITED_ENTITY_ATTRIBUTES = ["friendly_name"]

    self.bot.tree.add_command(
      app_commands.Command(
        name="get_entity",
        description="Retrieves information about an entity from Home Assistant",
        callback=self.get_entity
      ), 
      guild=discord.Object(self.bot.discord_main_guild_id) if self.bot.discord_main_guild_id is not None else None) # Get entity command

  async def entity_autocomplete(
      self,
      interaction: discord.Interaction,
      current_input: str
  ) -> List[app_commands.Choice[str]]:
    homeassistant_entities = self.bot.homeassistant_data_cache.get(homeassistant_cache_id.ENTITIES)
    if homeassistant_entities is None: # Need to fetch
      try:
        fetched_entities = self.bot.homeassistant_client.get_entities()
        if fetched_entities is not None:
          self.bot.homeassistant_data_cache[homeassistant_cache_id.ENTITIES] = fetched_entities
          homeassistant_entities = fetched_entities
        else:
          raise Exception("No entities were returned")
      except Exception as e:
        print("Failed to fetch the entities", e)
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

    min_score = choice_list[0][0] * (1 - self.bot.SIMILARITY_TOLERANCE) if len(choice_list) != 0 else 0
    return [x[1] for x in choice_list[:self.bot.MAX_AUTOCORRECT_CHOICES] if x[0] >= min_score]

  @app_commands.autocomplete(entity_id=entity_autocomplete)
  @app_commands.describe(entity_id="HomeAssistant entity identifier")
  @app_commands.checks.has_role(1398385337423626281) # TODO: Move to settings
  async def get_entity(self, interaction: discord.Interaction, entity_id: str):
    await interaction.response.defer()

    entity = self.bot.homeassistant_client.get_entity(entity_id=entity_id)
    history_url = add_param(urllib.parse.urljoin(self.bot.homeassistant_url, f"history"), entity_id=entity.entity_id)

    embed = discord.Embed(
      title=f"{str(entity.state.attributes["friendly_name"]) if "friendly_name" in entity.state.attributes else "?"}",
      description=entity.entity_id,
      color=discord.Colour.default(),
      timestamp=datetime.datetime.now()
    )

    embed.add_field(name="State", value=entity.state.state)
    embed.add_field(name="Last changed", value=str(entity.state.last_changed))
    embed.add_field(name="Last updated", value=str(entity.state.last_updated))
    embed.add_field(name="", value="Attributes", inline=False)
    for name, value in filter(lambda x: x[0] not in self.OMMITED_ENTITY_ATTRIBUTES, entity.state.attributes.items()):
      embed.add_field(name=name, value=str(value))

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Entity history", url=history_url))

    await interaction.followup.send(embed=embed, view=view)


async def setup(bot: HASSDiscordBot) -> None:
    await bot.add_cog(Entities(bot))