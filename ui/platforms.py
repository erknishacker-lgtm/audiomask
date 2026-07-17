"""Plataformas de hospedagem com logo (CDN Simple Icons)."""

from __future__ import annotations

from typing import Dict, List

# slug simpleicons / cor de marca
PLATFORMS: List[Dict[str, str]] = [
    {
        "id": "capcut",
        "name": "CapCut",
        "icon": "bytedance",
        "color": "000000",
        "hint_key": "hint_capcut",
    },
    {
        "id": "tiktok",
        "name": "TikTok",
        "icon": "tiktok",
        "color": "000000",
        "hint_key": "hint_tiktok",
    },
    {
        "id": "instagram",
        "name": "Instagram",
        "icon": "instagram",
        "color": "E4405F",
        "hint_key": "hint_instagram",
    },
    {
        "id": "facebook",
        "name": "Facebook",
        "icon": "facebook",
        "color": "1877F2",
        "hint_key": "hint_facebook",
    },
    {
        "id": "kwai",
        "name": "Kwai",
        "icon": "kuaishou",
        "color": "FF4906",
        "hint_key": "hint_kwai",
    },
    {
        "id": "youtube",
        "name": "YouTube",
        "icon": "youtube",
        "color": "FF0000",
        "hint_key": "hint_youtube",
    },
    {
        "id": "x",
        "name": "X (Twitter)",
        "icon": "x",
        "color": "000000",
        "hint_key": "hint_x",
    },
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "icon": "linkedin",
        "color": "0A66C2",
        "hint_key": "hint_linkedin",
    },
    {
        "id": "whatsapp",
        "name": "WhatsApp",
        "icon": "whatsapp",
        "color": "25D366",
        "hint_key": "hint_whatsapp",
    },
    {
        "id": "trello",
        "name": "Trello",
        "icon": "trello",
        "color": "0052CC",
        "hint_key": "hint_trello",
    },
]


def icon_url(icon: str, color: str = "FFFFFF") -> str:
    return f"https://cdn.simpleicons.org/{icon}/{color}"


def get_platform(pid: str) -> Dict[str, str]:
    for p in PLATFORMS:
        if p["id"] == pid:
            return p
    return {
        "id": "generic",
        "name": "Outra",
        "icon": "globe",
        "color": "2ECBFF",
        "hint_key": "hint_generic",
    }
