import requests
from flask import current_app

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

VALID_PRIORITIES = ('high', 'medium', 'low')

SYSTEM_PROMPT = (
    "You triage maintenance complaints for a residential society. Given a "
    "complaint's category, title and description, respond with exactly one "
    "word: high, medium, or low — how urgently it needs attention. Treat "
    "safety hazards (fire, sparking wires, gas smell, structural damage, "
    "flooding) as high, cosmetic or non-urgent issues as low. Respond with "
    "that single word and nothing else."
)


def suggest_priority(title, description, category):
    """Ask the configured OpenRouter model to triage a complaint's urgency.

    Returns 'high' / 'medium' / 'low', or None if no API key is configured
    or the call fails for any reason. None means "no suggestion available"
    — callers should proceed without one rather than treat it as an error,
    since this is an advisory enhancement, not a required step.
    """
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return None

    user_content = f"Category: {category}\nTitle: {title}\nDescription: {description}"

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
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_content},
                ],
                # gpt-oss-20b is a reasoning model — it spends completion
                # tokens "thinking" before the final word, so a small budget
                # gets cut off (finish_reason: length) before ever answering
                'max_tokens': 300,
                'temperature': 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        text = (content or '').strip().lower()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

    for priority in VALID_PRIORITIES:
        if priority in text:
            return priority
    return None
