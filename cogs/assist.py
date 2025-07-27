import discord
from discord import app_commands
from discord.ext import commands

from bot import HASSDiscordBot
from helpers import get_emoji

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

  @app_commands.describe(message = "Message to send", language = "Language")
  @app_commands.choices(language = [
    app_commands.Choice(name="Polish", value="pl"),
    app_commands.Choice(name="English", value="en"),
  ])
  async def assist(self, interaction: discord.Interaction, message: str, language: app_commands.Choice[str] = 'en'):
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
        response_data = self.bot.homeassistant_client.request(
          "conversation/process",
          method="POST",
          json=request_data
        )
      except Exception as e:
        print("Failed to reach homeassistant", e)
        return await interaction.followup.send(f"{get_emoji(False)} Failed to reach HomeAssistant.", ephemeral=True)
      
      # Update the conversation id cache
      if "conversation_id" in response_data and not preset_conversation_id:
        self.bot.conversation_cache[interaction.user.id] = response_data["conversation_id"]

      # Send the response
      if "response" in response_data:
        is_success = response_data["response"]["response_type"] in ['action_done', 'query_answer']
        plain_response_text = response_data["response"].get("speech", {}).get("plain", {}).get("speech")
        response_text = plain_response_text if plain_response_text is not None else "No text"
        await interaction.followup.send(f"{get_emoji(is_success)} {response_text}")
      else:
        await interaction.followup.send(f"⚠️ No response")
    except Exception as e:
      print("General error", e)
      await interaction.followup.send(f"{get_emoji(False)} Failed for unknown reason.", ephemeral=True)

async def setup(bot: HASSDiscordBot) -> None:
    await bot.add_cog(Assist(bot))