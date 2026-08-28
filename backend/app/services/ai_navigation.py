import requests
from flask import current_app

OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'

# Feature guide per role — kept in sync with the actual sidebar labels and
# routes in frontend/src/components/layout/AppSidebar.vue and
# frontend/src/router/index.js, not just plain-English feature names, so the
# model can point the user at a real page.
FEATURE_GUIDE = {
    'resident': (
        "- Complaints (sidebar: Complaints, /complaints): raise and track maintenance complaints, click 'Raise Complaint'\n"
        "- Amenities (sidebar: Amenities, /amenities): book clubhouse, gym and other shared amenities\n"
        "- Visitors (sidebar: Visitors, /visitors): pre-register expected guests\n"
        "- Maintenance Dues (sidebar: Maintenance, /maintenance): view and pay monthly dues\n"
        "- Notices (sidebar: Notices, /notices): read society announcements\n"
        "- Emergency (sidebar: Emergency, /emergency): raise an emergency alert\n"
        "- Profile (sidebar: Profile, /profile): update personal details\n"
        "- Documents (sidebar: Documents, /documents): request society documents/certificates\n"
        "- Home Services (/services): request vendor services directly (plumber, electrician, etc.)\n"
    ),
    'secretary': (
        "- Complaints (sidebar: Complaints, /sec/complaints): view and manage resident complaints, and assign vendors to them\n"
        "- Notices (sidebar: Notices, /sec/notices): post notices and broadcasts to residents\n"
        "- Emergency (sidebar: Emergency, /sec/emergency): manage and broadcast emergency alerts\n"
        "- Maintenance (sidebar: Maintenance, /sec/maintenance): manage resident dues payments\n"
        "- Residents (sidebar: Residents, /sec/residents): add and manage resident accounts, invite codes, and review resident profile update requests\n"
        "- Documents (sidebar: Documents, /sec/documents): review and process resident document requests\n"
        "- Amenities (sidebar: Amenities, /sec/amenities): manage amenities and approve/reject pending amenity bookings\n"
        "- Funds (sidebar: Funds, /sec/funds): manage society fund balances, transactions and fund split configuration\n"
        "- Vendors (sidebar: Vendors, /sec/vendors): manage the vendor directory\n"
        "- Vendor Jobs (sidebar: Vendor Jobs, /sec/vendors/jobs): track jobs assigned to vendors\n"
        "- Electricity Bills (sidebar: Electricity Bills, /sec/electricity): upload monthly bills and view AI usage analysis\n"
    ),
    'security': (
        "- Gate Dashboard (sidebar: Dashboard, /gate/dashboard): verify pre-registered visitors and log entries\n"
        "- Emergency (sidebar: Emergency, /gate/emergency): view and respond to emergency alerts\n"
        "- Notices (/notices): read society announcements\n"
    ),
}

FALLBACK_REPLY = 'Sorry, the assistant is currently unavailable. Please try again later.'


def build_system_prompt(role):
    guide = FEATURE_GUIDE.get(role, FEATURE_GUIDE['resident'])
    return (
        "You are the Niwaas Assistant, a help chatbot embedded in the Niwaas "
        f"residential society management app. The current user's role is '{role}'. "
        "Below is the COMPLETE and ACCURATE list of pages/features this role has "
        "access to — treat it as ground truth, not a starting point:\n\n"
        f"{guide}\n"
        "When the user asks how to do something, first check whether it matches "
        "any item in this list — including things mentioned inside an item's "
        "description, not just its title (e.g. vendor assignment is part of the "
        "Complaints item, not a separate one). If it matches, give short, concrete "
        "navigation steps referencing the sidebar label and the button/action to "
        "click — e.g. 'Go to Complaints in the sidebar, then click Raise Complaint.' "
        "Keep answers to 2-3 sentences. Only say a feature isn't available in Niwaas "
        "if it genuinely does not appear anywhere in this list, in the title or the "
        "description — never guess or assume something is missing without checking "
        "the full list first."
    )


def get_navigation_reply(role, message):
    """Returns the model's navigation guidance for `message`, or FALLBACK_REPLY
    if no API key is configured or the call fails — always a usable string,
    never raises, so the route can always return 200."""
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return FALLBACK_REPLY

    system_prompt = build_system_prompt(role)

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
                    {'role': 'user', 'content': message},
                ],
                'max_tokens': 600,
                'temperature': 0.3,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        reply = (content or '').strip()
    except (requests.RequestException, KeyError, IndexError, ValueError) as e:
        resp = locals().get('response')
        body = f' | response body: {resp.text[:500]}' if resp is not None else ''
        current_app.logger.warning(f'[ai_navigation] failed: {e}{body}')
        return FALLBACK_REPLY

    return reply or FALLBACK_REPLY