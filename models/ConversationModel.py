from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

class ConversationResponseType(str, Enum):
  ACTION_DONE = 'action_done'
  QUERY_ANSWER = 'query_answer'
  ERROR = 'error'

class ConversationErrorCode(str, Enum):
  NO_INTENT_MATCH = 'no_intent_match' # The input text did not match any intents.
  NO_VALID_TARGETS = 'no_valid_targets' # The targeted area, device, or entity does not exist.
  FAILED_TO_HANDLE = 'failed_to_handle' # An unexpected error occurred while handling the intent.
  UNKNOWN = 'unknown' # An error occurred outside the scope of intent processing.

class ConversationCard(BaseModel):
  pass # Card?

class ConversationTarget(BaseModel):
  type: str
  name: str
  id: str

class ConversationData(BaseModel):
  targets: Optional[List[ConversationTarget]] = None # Area / domain
  success: Optional[List[ConversationTarget]] = None # Device / entity
  failed: Optional[List[ConversationTarget]] = None # Device / entity
  code: Optional[ConversationErrorCode] = None # Error code

class ConversationSpeechPlain(BaseModel):
  speech: str
  extra_data: None = None

class ConversationSpeech(BaseModel):
  plain: Optional[ConversationSpeechPlain] = None
  # ssml

class ConversationResponse(BaseModel):
  language: str
  card: ConversationCard
  data: ConversationData
  speech: ConversationSpeech
  response_type: ConversationResponseType
  speech_slots: Optional[Dict[str, str]] = None # Undocumented?

class ConversationModel(BaseModel):
  response: ConversationResponse
  conversation_id: Optional[str]
  continue_conversation: bool
