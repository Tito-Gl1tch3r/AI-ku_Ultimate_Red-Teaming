import requests
import hashlib
import sys


class Checker:
    def __init__(self):
        pass

    def request_api_data(self, query_char):
        url = 'https://api.pwnedpasswords.com/range/' + query_char
        res = requests.get(url)
        if res.status_code != 200:
            raise RuntimeError(
                f'Error fetching: {res.status_code}, check the api and try again')
        return res

    def get_password_leaks_count(self, hashes, hash_to_check):
        hashes = (line.split(':') for line in hashes.text.splitlines())
        for h, count in hashes:
            if h == hash_to_check:
                return count
        return 0

    def pwned_api_check(self, password):
        sha1password = hashlib.sha1(
            password.encode('utf-8')).hexdigest().upper()
        first5_char, tail = sha1password[:5], sha1password[5:]
        response = Checker.request_api_data(0, first5_char)
        return Checker.get_password_leaks_count(0, response, tail)

    def main(self, args):
        for password in args:
            count = Checker.pwned_api_check(0, password)
            if count:
                print(
                    f'{password} was found {count} times \U0001F62C... you should probably change your password!')
            else:
                print(f'{password} was NOT found. Carry on!')
                print("Leading You To The Safe Land", "\N{winking face}")
