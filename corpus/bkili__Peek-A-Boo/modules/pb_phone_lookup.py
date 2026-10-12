# /modules/pb_phone_lookup.py
from modules.base import BaseModule
import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests


class Module(BaseModule):
    def __init__(self):
        super().__init__()
        self.name = "pb_phone_lookup"
        self.description = (
            "Analyze phone numbers using phonenumbers library "
            "and optional NumVerify API."
        )
        self.category = "osint"
        self.author = "022NN"
        self.author_email = "n0220n@proton.me"
        self.url = "https://github.com/bkili"
        self.license = ""
        self.version = "0.0.1"
        self.options = {"phone_number": "", "numverify_api_key": ""}
        self.required_options = ["phone_number"]

    def run(self, shared_data):
        phone = self.options["phone_number"]
        api_key = self.options.get("numverify_api_key", "")

        try:
            parsed = phonenumbers.parse(phone, None)
            valid = phonenumbers.is_valid_number(parsed)
            formatted = phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL
            )
            region = geocoder.description_for_number(parsed, "en")
            provider = carrier.name_for_number(parsed, "en")
            time = timezone.time_zones_for_number(parsed)

            print(f"\n[+] Formatted: {formatted}")
            print(f"[+] Valid: {valid}")
            print(f"[+] Region: {region}")
            print(f"[+] Carrier: {provider}")
            print(f"[+] Timezone: {time}\n")

            result = {
                "formatted": formatted,
                "valid": valid,
                "region": region,
                "carrier": provider,
            }

            # ---------- NumVerify ----------
            if api_key:
                url = f"http://apilayer.net/api/validate?access_key={api_key}&number={phone}&format=1"  # noqa: E501
                response = requests.get(url)
                if response.ok:
                    data = response.json()
                    print("\n[+] NumVerify Data:")
                    print(f"  - Line Type: {data.get('line_type', '-')}")
                    print(f"  - Location : {data.get('location', '-')}")
                    print(f"  - Carrier  : {data.get('carrier', '-')}")
                    print(f"  - Country  : {data.get('country_name', '-')}")
                    result.update(
                        {
                            "numverify_line_type": data.get("line_type"),
                            "numverify_location": data.get("location"),
                            "numverify_carrier": data.get("carrier"),
                            "numverify_country": data.get("country_name"),
                        }
                    )
                else:
                    print("[!] NumVerify API request failed.")

            shared_data["last_summary"] = result

        except Exception as e:
            print(f"[!] Error: {e}")

    def print_summary(self, summary):
        try:
            print(f"\nSummary for {summary.get('formatted', '-')}")
            print(f"Valid       : {summary.get('valid', '-')}")
            print(f"Region      : {summary.get('region', '-')}")
            print(f"Carrier     : {summary.get('carrier', '-')}")
            if "numverify_country" in summary:
                print("NumVerify:")
                print(f"  Country   : {summary.get('numverify_country')}")
                print(f"  Location  : {summary.get('numverify_location')}")
                print(f"  Carrier   : {summary.get('numverify_carrier')}")
                print(f"  Line Type : {summary.get('numverify_line_type')}")
        except Exception as e:
            print(f"[!] Error: {e}")
