import requests
import json
from flask import url_for
from . import config
from .util import HkfreeRole

def send_slack_webhook(webhook_url, payload):
    try:
        response = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        if response.status_code != 200:
            print(f"ERROR send_slack_webhook: ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"ERROR send_slack_webhook: {e}")

def notify_new_proposal(proposal_type, proposal_id, subject, author_name, cost, description, full_url):
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Nový návrh pro {proposal_type.long_name} - {subject}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Cena:*\n{cost} Kč"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Odkaz:*\n<{full_url}|Otevřít návrh>"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Navrhovatel:*\n{author_name}"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Popis:*\n{description}" 
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Hlasovat / Zobrazit",
                            "emoji": True
                        },
                        "value": str(proposal_id),
                        "url": full_url,
                        "action_id": "view_proposal"
                    }
                ]
            }
        ]
    }

    if hasattr(config, 'SLACK_WEBHOOK_URL') and config.SLACK_WEBHOOK_URL:
        match proposal_type:
            case HkfreeRole.VV:
                send_slack_webhook(config.SLACK_WEBHOOK_URL_VV, payload)
            case HkfreeRole.PD:
                send_slack_webhook(config.SLACK_WEBHOOK_URL_PD, payload)
            case HkfreeRole.CS:
                send_slack_webhook(config.SLACK_WEBHOOK_URL_CS, payload)
                
    else:
        print("WARNING: SLACK_WEBHOOK_URL není nastaveno v config.py")