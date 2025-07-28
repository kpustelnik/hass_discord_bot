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
  conversation_id: str
  continue_conversation: bool
'''
{'response': {'speech': {'plain': {
  'speech': 'Turned off the lights', 'extra_data': None}}, 
  'card': {}, 'language': 'en', 'response_type': 'action_done', 'data': {'targets': [], 
                                                      'success': [{'name': 'Salon', 'type': 'area', 'id': 'salon'}, {'name': 'Salon sufit', 'type': 'entity', 'id': 'light.salon_sufit'}, {'name': 'Salon lampa stojąca', 'type': 'entity', 'id': 'light.salon_lampa_stojaca'}, {'name': 'Salon lampa TV', 'type': 'entity', 'id': 'light.salon_lampa_tv'}, {'name': 'Salon lampa stojąca', 'type': 'entity', 'id': 'light.salon_lampa_stojaca_3'}, {'name': 'Salon sufit', 'type': 'entity', 'id': 'light.salon_sufit_3'}, {'name': 'Salon lampa TV', 'type': 'entity', 'id': 'light.salon_lampa_tv_3'}], 'failed': []}}, 'conversation_id': '01K1842KJSV65GG963FKWQY1NY', 'continue_conversation': False}

{'response': {'speech': {'plain': {'speech': "Sorry, I couldn't understand that", 'extra_data': None}}, 'card': {}, 'language': 'en', 'response_type': 'error', 'data': {'code': 'no_intent_match'}}, 'conversation_id': '01K1842KJSV65GG963FKWQY1NY', 'continue_conversation': False}

{'speech': {'plain': {'speech': '11:01 AM', 'extra_data': None}}, 'card': {}, 'language': 'en', 
              'response_type': 'action_done', 'speech_slots': {'time': '11:01:48.047857'}, 'data': {'targets': [], 'success': [], 'failed': []}}
              '''