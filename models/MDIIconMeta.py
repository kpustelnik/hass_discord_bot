from pydantic import BaseModel
from typing import List, Optional

class MDIIconMeta(BaseModel):
  id: str
  baseIconId: str
  name: str
  codepoint: str
  aliases: List[str]
  styles: List[str]
  version: str
  deprecated: bool
  tags: List[str]
  author: str