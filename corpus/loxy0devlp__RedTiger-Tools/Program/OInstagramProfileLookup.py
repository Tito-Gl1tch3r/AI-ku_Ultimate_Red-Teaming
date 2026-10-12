# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def Lookup(target, sessionid, http_proxy, useragent):
    logging.getLogger("instaloader").setLevel(logging.CRITICAL)
    loader                          = instaloader.Instaloader(download_pictures=False, download_videos=False, save_metadata=False, quiet=True)
    loader.context.log              = lambda *args, **kwargs: None
    loader.context.error            = lambda *args, **kwargs: None
    if http_proxy: loader.context._session.proxies = {"http": f"http://{http_proxy}", "https": f"http://{http_proxy}"}
    if useragent : loader.context._session.headers.update({"User-Agent": useragent})
    try: loader.context._session.cookies.set("sessionid", sessionid, domain=".instagram.com")
    except: ErrorSession()

    try: profile = instaloader.Profile.from_username(loader.context, target)
    except Exception as e:
        Error(f"Profile access error: {white}{e}")
        Continue()
        Reset()

    profile_infos = {
        "Username"               : profile.username,
        "Full name"              : profile.full_name,
        "User ID"                : profile.userid,
        "Biography"              : profile.biography,
        "Biography hashtags"     : " / ".join(profile.biography_hashtags) if profile.biography_hashtags else None,
        "Biography mentions"     : " / ".join(profile.biography_mentions) if profile.biography_mentions else None,
        "External URL"           : profile.external_url,
        "Followers"              : profile.followers,
        "Followees"              : profile.followees,
        "Posts count"            : profile.mediacount,
        "Reels count"            : profile.igtvcount,
        "Is private"             : profile.is_private,
        "Is verified"            : profile.is_verified,
        "Is business account"    : profile.is_business_account,
        "Business category name" : profile.business_category_name,
        "Has public story"       : profile.has_public_story,
        "Has viewable story"     : profile.has_viewable_story,
        "Has highlight reels"    : profile.has_highlight_reels,
        "Blocked by viewer"      : profile.blocked_by_viewer,
        "Has blocked viewer"     : profile.has_blocked_viewer,
        "Followed by viewer"     : profile.followed_by_viewer,
        "Follows viewer"         : profile.follows_viewer,
        "Requested by viewer"    : profile.requested_by_viewer,
        "Has requested viewer"   : profile.has_requested_viewer,
        "Profile URL"            : f"https://www.instagram.com/{profile.username}",
        "Profile picture URL"    : profile.profile_pic_url,
    }

    vars = {k: str(v) for k, v in profile_infos.items() if v is not None}
    for name, value in vars.items(): Add(f"{name}: {white + str(value)}")
    return profile_infos

def InstagramProfileLookup(target=None, sessionid=None, http_proxy=None, useragent=None, output=None):
    Title("Instagram Profile Lookup")

    if not target   : target    = Input("Username [-u] -> ")
    if not sessionid: sessionid = Input(f"Your session ID [-s] (default: {str(default_instagram_session_id)}) -> ")

    if not has_cli_args: 
        http_proxy   = Input(f"HTTP proxy [-HP] (default: {str(default_http_proxy)}) -> ")
        useragent    = Input(f"User-Agent [-u] (for random: random, default: {str(default_useragent)}) -> ")

    if not sessionid : sessionid  = default_instagram_session_id
    if not http_proxy: http_proxy = default_http_proxy
    if not useragent : useragent  = default_useragent

    Info(f"Session ID: {white}{sessionid}")
    session, proxies, cookie, useragent = EnableHttpProxyAndUserAgentAndCookie(http_proxy=http_proxy, useragent=useragent, http_timeout=default_http_timeout, enable_cookie=False)

    Wait("Scanning..")
    profiles_infos = Lookup(target, sessionid, http_proxy, useragent)

    json_data = {
        "Parameters": {
            "Session ID": sessionid,
            "HTTP proxy": http_proxy if http_proxy else None,
            "User-agent": useragent if useragent else None
        },
        "Informations": profiles_infos,
    }

    if output in (True, None): SaveJsonToFile(json_data, f"Result_InstagramProfileLookup_{target}", json_output=output)
    Continue()
    Reset()