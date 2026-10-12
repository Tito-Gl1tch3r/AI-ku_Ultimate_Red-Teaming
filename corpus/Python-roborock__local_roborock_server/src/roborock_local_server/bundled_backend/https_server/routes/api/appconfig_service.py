"""Shared app-config data for v1/v2 appconfig endpoints."""

from __future__ import annotations

from typing import Any

APP_CONFIG_COMMON_DATA: dict[str, Any] = {
    "version": "4.41.04",
    "url": "itms-apps://itunes.apple.com/cn/app/id1462875428?mt=8",
    "required": 0,
    "description": "<p><br></p>",
    "minimumVersion": "0.0.0",
    "mainPictureInfoList": [
        {
            "darkModePic": "https://files.roborock.com/iot/doc/bbecbae006b940eab34d200ba809bb72.png",
            "lightModePic": "https://files.roborock.com/iot/doc/a35d5dfcd6eb41e69dab160fe12f059f.png",
        },
        {
            "darkModePic": "https://files.roborock.com/iot/doc/588414a901d645058c9dce93b5f891c3.png",
            "lightModePic": "https://files.roborock.com/iot/doc/e38de51323a743628f094358611c6b0d.png",
        },
        {
            "darkModePic": "https://files.roborock.com/iot/doc/576cfc12bed843c9b45bffabceb07259.png",
            "lightModePic": "https://files.roborock.com/iot/doc/de2f035553f24795a5699279193d312a.png",
        },
    ],
}


def app_config_common_payload() -> dict[str, Any]:
    return dict(APP_CONFIG_COMMON_DATA)
