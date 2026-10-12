# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def Lookup(phone):
    
    try: parsed = phonenumbers.parse(phone, None)
    except: ErrorNumberFormat()

    try:    phone_e164          = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except: phone_e164          = None
    try:    phone_international = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    except: phone_international = None
    try:    phone_national      = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL)
    except: phone_national      = None
    try:    phone_valid         = phonenumbers.is_valid_number(parsed)
    except: phone_valid         = None
    try:    phone_possible      = phonenumbers.is_possible_number(parsed)
    except: phone_possible      = None
    try:    phone_country_code  = f"+{parsed.country_code}"
    except: phone_country_code  = None
    try:    phone_country       = phonenumbers.region_code_for_number(parsed)
    except: phone_country       = None
    try:    phone_region        = phonenumbers.geocoder.description_for_number(parsed, "fr")
    except: phone_region        = None
    try:    phone_carrier_name  = phonenumbers.carrier.name_for_number(parsed, "fr")
    except: phone_carrier_name  = None

    try:
        number_type = phonenumbers.number_type(parsed)
        if number_type == phonenumbers.PhoneNumberType.MOBILE:       phone_number_type = "Mobile"
        elif number_type == phonenumbers.PhoneNumberType.FIXED_LINE: phone_number_type = "Fixe"
        else:                                                        phone_number_type = str(number_type)
    except:                                                          phone_number_type = None

    try:
        tz = phonenumbers.timezone.time_zones_for_number(parsed)
        phone_timezones = " / ".join(tz) if tz else None
    except: phone_timezones = None

    phone_infos = {
        "Phone number"       : phone,
        "Phone E164"         : phone_e164,
        "Phone international": phone_international,
        "Phone national"     : phone_national,
        "Phone valid"        : phone_valid,
        "Phone possible"     : phone_possible,
        "Phone country code" : phone_country_code,
        "Phone country"      : phone_country,
        "Phone region"       : phone_region,
        "Phone carrier"      : phone_carrier_name,
        "Phone number type"  : phone_number_type,
        "Phone timezones"    : phone_timezones
    }

    vars = {k: str(v) for k, v in phone_infos.items() if v is not None}
    for name, value in vars.items(): Add(f"{name}: {white + str(value)}")
    return phone_infos

def Links(phone, phone_country):
    phone = phone.replace("+", "%2B")
    urls = {
        "Google"       : f"https://google.com/search?q=%22{phone}%22",
        "Bing"         : f"https://bing.com/search?q=%22{phone}%22",
        "Duckduckgo"   : f"https://duckduckgo.com/?q=%22{phone}%22",
        "Pagesjaunes"  : f"https://pagesjaunes.fr/annuaireinverse/recherche?quoiqui={phone}",
        "Truecaller"   : f"https://truecaller.com/search/{phone_country}/{phone}",
        "Whitepages"   : f"https://whitepages.com/phone/{phone}",
        "AnyWho"       : f"https://anywho.com/phone/{phone}",
        "ThatsThem"    : f"https://thatsthem.com/phone/{phone}",
        "Gelbeseiten"  : f"https://gelbeseiten.de/suche/{phone}",
        "PagineBianche": f"https://paginebianche.it/aziende?qs={phone}"
    }

    Info("Targeted links:")
    for name, url in urls.items():
        print(f"               {red}- {name:<{max(len(name) for name in urls.keys())}} : {white + url}")
    return urls

def PhoneNumerLookup(phone=None, output=None):
    Title("Phone Numer Lookup")

    if not phone: phone = Input("Phone [-p] -> ")

    Wait("Scanning..")
    phone_infos = Lookup(phone)
    urls        = Links(phone, phone_infos["Phone country"])

    json_data = {
        "Informations": phone_infos,
        "Targeted links": urls
    }

    if output in (True, None): SaveJsonToFile(json_data, f"Result_PhoneNumerLookup_{phone}", json_output=output)
    Continue()
    Reset()