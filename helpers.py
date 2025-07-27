import re
from Levenshtein import distance as levenshtein_distance

def get_emoji(success: bool):
  """Returns the success or error emoji"""
  if success:
    return '✅'
  else:
    return '❌'
  
def add_param(url, **params):
    """Add query parameters to url"""
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    u = urlparse(url)
    q = parse_qs(u.query)
    q.update({k: [v] for k, v in params.items()})
    return urlunparse(u._replace(query=urlencode(q, doseq=True)))

def shorten_option_name(name):
  """Shortens Discord choice option (max 100 characters)"""
  if len(name) > 100:
    return f"{name[:97]}..."
  return name
  
# Tokenizing identifiers and calculating their similarity (mostly for autocompletion feature)
  
def tokenize(text: str) -> list[str]:
  """Tokenizes and normalizes a string into keywords."""
  text = text.lower()
  tokens = re.split(r'[^a-zA-Z0-9]', text)
  return [t for t in tokens if t]

def fuzzy_keyword_match(target_tokens: list[str], input_tokens: list[str]) -> float:
  """
  Scores how well input_tokens match target_tokens using Levenshtein distance.
  Higher = better (1.0 = perfect match).
  """
  if not input_tokens or not target_tokens: # len != 0
    return 0.0
  
  score = 0.0
  for user_token in input_tokens:
    best = min(
      levenshtein_distance(user_token, target_token) / max(len(user_token), len(target_token))
      for target_token in target_tokens
    )
    score += 1 - best  # convert distance to similarity

  return score / len(input_tokens)  # average similarity

def fuzzy_keyword_match_with_order(target_tokens: list[str], input_tokens: list[str]) -> float:
  """
  Scores how well input_tokens match target_tokens using Levenshtein distance.
  Takes the word order into account
  """
  if not input_tokens or not target_tokens: # len != 0
    return 0.0

  total_similarity = 0.0
  match_indexes = []

  for user_token in input_tokens:
    best_score = float('inf')
    best_index = -1
    for i, target_token in enumerate(target_tokens):
      norm = levenshtein_distance(user_token, target_token) / max(len(user_token), len(target_token))
      if norm < best_score:
        best_score = norm
        best_index = i
    total_similarity += 1 - best_score # similarity
    match_indexes.append(best_index)

  average_similarity = total_similarity / len(input_tokens)

  # Count how many matched indexes are in increasing order
  order_score = sum(
    1 for i in range(1, len(match_indexes))
    if match_indexes[i] > match_indexes[i - 1]
  ) / len(match_indexes)

  # Final score: mostly fuzzy match + small bonus for order
  return 0.9 * average_similarity + 0.1 * order_score