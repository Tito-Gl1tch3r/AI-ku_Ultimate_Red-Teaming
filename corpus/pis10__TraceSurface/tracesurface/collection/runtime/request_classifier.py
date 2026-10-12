from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from tracesurface.policies import StaticResourcePolicy, TargetContext, ThirdPartyPolicy


@dataclass(frozen=True, slots=True)
class RequestClassification:
    keep: bool
    is_js: bool = False


class RequestClassifier:
    def __init__(
        self,
        third_party: ThirdPartyPolicy | None = None,
        static_policy: StaticResourcePolicy | None = None,
    ) -> None:
        self.third_party = third_party or ThirdPartyPolicy()
        self.static_policy = static_policy or StaticResourcePolicy()

    def classify_cdp_request(
        self,
        url: str,
        req_type: str,
        target: TargetContext,
    ) -> RequestClassification:
        clean_url = url.split("?", 1)[0]

        if req_type == "Script":
            if self.third_party.is_third_party(clean_url, target):
                return RequestClassification(False)
            if urlparse(clean_url).path.endswith(".js"):
                return RequestClassification(True, is_js=True)
            return RequestClassification(False)

        if req_type not in ("Fetch", "XHR"):
            return RequestClassification(False)

        if self.third_party.is_third_party(url, target):
            return RequestClassification(False)

        if self.static_policy.is_static_resource_url(clean_url):
            is_js = urlparse(clean_url).path.endswith(".js")
            return RequestClassification(False, is_js=is_js)

        return RequestClassification(True)


def is_business_js(
    url: str,
    target: TargetContext | None = None,
    third_party: ThirdPartyPolicy | None = None,
) -> bool:
    policy = third_party or ThirdPartyPolicy()

    if policy.is_third_party(url, target):
        return False

    parsed = urlparse(url)
    return bool(parsed.netloc and url.endswith(".js"))
