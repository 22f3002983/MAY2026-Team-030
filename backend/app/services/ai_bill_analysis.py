import requests
from flask import current_app

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

SYSTEM_PROMPT = (
    "You are analysing electricity bills for a residential society. Given "
    "the current month's units consumed and amount, plus up to 3 previous "
    "months for comparison, write a short analysis (3-5 sentences) covering: "
    "whether this month is higher or lower than the recent average, any "
    "anomaly worth flagging, and one practical recommendation for the "
    "society. Plain text only, no markdown."
)


def analyze_electricity_bill(current_bill, previous_bills):
    """current_bill: {'month', 'total_units', 'total_amount'}
    previous_bills: list of the same shape, most recent first (up to 3).

    Returns a plain-text analysis string, or None if no API key is
    configured or the call fails for any reason — callers should store
    None and let the frontend show 'Analysis pending' rather than treat
    this as an error.
    """
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return None

    lines = [
        f"Current month ({current_bill['month']}): "
        f"{current_bill['total_units']} units, Rs.{current_bill['total_amount']}"
    ]
    if previous_bills:
        lines.append('Previous months:')
        for b in previous_bills:
            lines.append(f"- {b['month']}: {b['total_units']} units, Rs.{b['total_amount']}")
    else:
        lines.append('No previous months on record for comparison.')
    user_content = '\n'.join(lines)

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
                # before it emits the final analysis (see ai_priority.py)
                'max_tokens': 700,
                'temperature': 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        text = (content or '').strip()
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return None

    return text or None
