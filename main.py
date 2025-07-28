import logging
import os
import sys

from dotenv import load_dotenv
from bot import HASSDiscordBot

load_dotenv() # Load the dotenv

logger = logging.getLogger("HASS_Discord_Bot")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)

HASSDiscordBot(
  logger=logger
).run(os.getenv("DISCORD_TOKEN")) # Run the bot