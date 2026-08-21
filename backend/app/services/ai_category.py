import requests
from flask import current_app

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


def suggest_category(text, valid_categories):
    """Ask the configured OpenRouter model to classify free text into one of
    valid_categories. Returns the matching category string, or None if no
    API key is configured or the call fails/doesn't match — callers should
    proceed without a suggestion rather than treat None as an error.
    """
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return None

    options = ', '.join(valid_categories)
    system_prompt = (
        "You classify maintenance/service descriptions for a residential society. "
        f"Given the text, respond with exactly one word from this list: {options}. "
        "Pick whichever category the described problem or service best fits. "
        "Respond with that single word and nothing else."
    )

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': current_app.config['OPENROUTER_MODEL'],
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': text},
                ],
                # gpt-oss-20b is a reasoning model — needs headroom to think
                # before it emits the final word (see ai_priority.py)
                'max_tokens': 300,
                'temperature': 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        text_out = (content or '').strip().lower()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

    for category in valid_categories:
        if category in text_out:
            return category
    return None
