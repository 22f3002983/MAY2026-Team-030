import requests
from flask import current_app

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

SYSTEM_PROMPT = (
    "You write short secretary-facing summaries of community maintenance "
    "issues for a residential society. Given an issue's title, category, and "
    "one or more resident reports describing it, write a single concise "
    "paragraph (2-3 sentences) that summarizes the issue clearly for someone "
    "triaging it — merge overlapping details, don't just repeat each report "
    "verbatim. Do not mention resident names or how many people reported it. "
    "Respond with only the summary paragraph, nothing else."
)


def suggest_summary(title, category, descriptions):
    """Ask the configured OpenRouter model to merge one or more resident
    reports on the same issue into a single secretary-facing summary.

    Returns the summary text, or None if no API key is configured or the
    call fails — callers should proceed without one (falling back to the
    raw description) rather than treat None as an error.
    """
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return None

    reports_text = '\n'.join(f'- {d}' for d in descriptions if d)
    if not reports_text:
        return None

    user_content = f"Title: {title}\nCategory: {category}\nReports:\n{reports_text}"

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
                # generous headroom — gpt-oss-20b "thinks" before writing the
                # actual summary, and the summary itself can run a few
                # sentences (see ai_priority.py for why this matters)
                'max_tokens': 500,
                'temperature': 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        summary = (content or '').strip()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

    return summary or None
