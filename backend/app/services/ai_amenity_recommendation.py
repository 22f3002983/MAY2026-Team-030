import requests
from flask import current_app


OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'


SYSTEM_PROMPT = (
    "You help residents of a housing society find the right amenity for what "
    "they want to do. Given the list of currently available amenities and "
    "what the resident is looking for, recommend the single best match, or "
    "explain why none are suitable and mention what is available instead. "
    "Keep the response to 2-3 sentences, plain text, no markdown. Only "
    "recommend amenities from the provided list — never invent one."
)

NONE_AVAILABLE_MESSAGE = (
    "Nothing is available right now — every amenity is either booked, under "
    "maintenance, or closed. Please check back later."
)
EMPTY_RESPONSE_FALLBACK = (
    "I couldn't find a suitable match for that — try describing what you're "
    "looking for a bit differently."
)


def recommend_amenity(amenities, query):
    """amenities: list of {'name', 'type', 'status', 'description'}.

    Returns a plain-text recommendation/explanation string in the normal
    case — including when nothing fits the request — or None only when the
    AI call itself couldn't be made or failed (no API key, network error,
    malformed response). Callers should treat None as 'AI recommendation
    unavailable' and any string, including the built-in fallbacks below, as
    a normal answer to show the resident.
    """
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return None

    # Only amenities that are actually usable right now, and that make
    # sense as an "activity" recommendation, should ever reach the model —
    # otherwise it may recommend something booked/under maintenance, or
    # infrastructure like a water tank that isn't something you'd "go do".
    candidates = [
        a for a in amenities
        if a.get('status') == 'available' and a.get('type') != 'unbookable'
    ]

    if not candidates:
        # Nothing to recommend — answer deterministically, no need to call
        # the model (and no risk of it hallucinating a match anyway).
        return NONE_AVAILABLE_MESSAGE

    listing = '\n'.join(
        f"- {a['name']} ({a['type']}, {a['status']})" + (f": {a['description']}" if a['description'] else '')
        for a in candidates
    )

    user_content = (
        f"Here are the currently available amenities in Niwaas society:\n{listing}\n\n"
        f"Resident is looking for: {query}\n\n"
        "Recommend the best match from this list, or explain why none are "
        "suitable and mention what is available instead."
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
                # gpt-oss-20b is a reasoning model — needs headroom to think
                # before it emits the final recommendation (see ai_priority.py)
                'max_tokens': 500,
                'temperature': 0.3,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        text = (content or '').strip()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

    return text or EMPTY_RESPONSE_FALLBACK