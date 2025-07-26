def conditional_decorator(decorator, condition: bool):
    def wrapper(func):
        return decorator(func) if condition else func
    return wrapper

def get_emoji(success: bool):
  if success:
    return '✅'
  else:
    return '❌'