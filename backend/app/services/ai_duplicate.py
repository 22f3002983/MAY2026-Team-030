import re
import requests
from flask import current_app

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

SYSTEM_PROMPT = (
    "You detect duplicate reports for a residential society's issue tracker. "
    "Given a NEW report and a numbered list of EXISTING open issues in the "
    "same category, identify which existing issue numbers (if any) describe "
    "the same underlying problem as the new report — even if worded "
    "differently. Respond with only the matching numbers separated by "
    'commas (e.g. "2,5"), or the single word "none" if nothing matches. '
    "Respond with nothing else."
)


def find_semantic_duplicates(new_title, new_description, candidates):
    """candidates: list of {'id', 'title', 'description'} dicts — open issues
    in the same category, excluding ones the reporting resident is already
    part of. Returns the subset of candidate ids the model thinks describe
    the same problem as the new report, or [] if no key is configured, the
    call fails, or nothing matches — callers should treat [] as "no
    suggestion", not an error, and let the resident raise as normal.
    """
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key or not candidates:
        return []

    numbered = '\n'.join(
        f"{i + 1}. Title: {c['title']}\n   Description: {c['description']}"
        for i, c in enumerate(candidates)
    )
    user_content = (
        f"NEW REPORT:\nTitle: {new_title}\nDescription: {new_description}\n\n"
        f"EXISTING ISSUES:\n{numbered}"
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
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': user_content},
                ],
                'max_tokens': 400,
                'temperature': 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        text = (content or '').strip().lower()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return []

    if 'none' in text:
        return []

    matched_ids = []
    for n in re.findall(r'\d+', text):
        idx = int(n) - 1
        if 0 <= idx < len(candidates):
            matched_ids.append(candidates[idx]['id'])
    return matched_ids
