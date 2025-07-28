import discord
from discord import app_commands
from discord.ext import commands
import datetime
import os

from bot import HASSDiscordBot
from enums.emojis import Emoji
from models.ConversationModel import ConversationResponseType

class Assist(commands.Cog):
  def __init__(self, bot: HASSDiscordBot) -> None:
    self.bot = bot

    self.bot.tree.add_command(
      app_commands.Command(
        name="assist",
        description="Processes Home Assistant conversation",
        callback=self.assist
      ), 
      guild=discord.Object(self.bot.discord_main_guild_id) if self.bot.discord_main_guild_id is not None else None) # Assist command

    self.details = True

  @app_commands.describe(message = "Message to send", language = "Language")
  @app_commands.choices(language = [
    app_commands.Choice(name="Polish", value="pl"),
    app_commands.Choice(name="English", value="en"),
  ])
  async def assist(self, interaction: discord.Interaction, message: str, language: app_commands.Choice[str] = os.getenv('DEFAULT_LANGUAGE')):
    try:
      await interaction.response.defer(thinking=True) # Notify Discord

      # Construct the request body
      request_data = {
        "text": message,
        "language": language
      }
      preset_conversation_id = self.bot.conversation_cache.get(interaction.user.id) is not None
      if preset_conversation_id:
        request_data["conversation_id"] = self.bot.conversation_cache.get(interaction.user.id)
      
      # Send the request to home assistant
      try:
        response_data = self.bot.homeassistant_client.custom_conversation(request_data)
      except Exception as e:
        self.bot.logger.error("Failed to reach HomeAssistant", e)
        return await interaction.followup.send(f"{Emoji.ERROR} Failed to reach HomeAssistant.", ephemeral=True)
      
      # Update the conversation id cache
      if response_data.conversation_id is not None and not preset_conversation_id:
        self.bot.conversation_cache[interaction.user.id] = response_data.conversation_id

      # Send the response
      if response_data.response is not None:
        plain_response_text = response_data.response.speech.plain.speech if response_data.response.speech is not None and response_data.response.speech.plain is not None and response_data.response.speech.plain.speech is not None else None
        
        response_text = plain_response_text if plain_response_text is not None else "No text"
        is_success = response_data.response.response_type in [ConversationResponseType.ACTION_DONE, ConversationResponseType.QUERY_ANSWER]
        
        embed = discord.Embed(
          title="Conversation result",
          description=f"{Emoji.SUCCESS if is_success else Emoji.ERROR} {response_text}",
          color=discord.Colour.default(),
          timestamp=datetime.datetime.now()
        )

        if response_data.response.data is not None and self.details:
          if response_data.response.data.targets is not None and len(response_data.response.data.targets) > 0:
            embed.add_field(name="Targets", value='\n'.join([ f'{target.type} - {target.name} ({target.id})' for target in response_data.response.data.targets ]))
          if response_data.response.data.success is not None and len(response_data.response.data.success) > 0:
            embed.add_field(name="Successfully changed", value='\n'.join([ f'{target.type} - {target.name} ({target.id})' for target in response_data.response.data.success ]))
          if response_data.response.data.failed is not None and len(response_data.response.data.failed) > 0:
            embed.add_field(name="Failed to change", value='\n'.join([ f'{target.type} - {target.name} ({target.id})' for target in response_data.response.data.failed ]))

          if response_data.response.data.code is not None:
            embed.add_field(name="Error code", value=response_data.response.data.code)

        await interaction.followup.send(embed=embed)
      else:
        await interaction.followup.send(f"{Emoji.WARNING} No response")
    except Exception as e:
      self.bot.logger.error("General error", e)
      await interaction.followup.send(f"{Emoji.ERROR} Failed for unknown reason.", ephemeral=True)

async def setup(bot: HASSDiscordBot) -> None:
  await bot.add_cog(Assist(bot))