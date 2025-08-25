import logging
from logging.handlers import RotatingFileHandler
import os
import sys

from dotenv import load_dotenv
from bot import HASSDiscordBot

load_dotenv() # Load the dotenv

logger = logging.getLogger("stdout")
logger.setLevel(logging.INFO)

file_logger = logging.getLogger("file")
file_logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"))
file_handler = RotatingFileHandler(
  'logs/usage.log',
  maxBytes=25*1024*1024, 
  backupCount=5
)
file_handler.setFormatter(logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"))
logger.addHandler(handler)
file_logger.addHandler(handler)
file_logger.addHandler(file_handler)

HASSDiscordBot(
  logger=logger,
  file_logger=file_logger
).run(os.getenv("DISCORD_TOKEN")) # Run the bot
