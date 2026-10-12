from flask.sessions import SecureCookieSessionInterface
from itsdangerous import URLSafeTimedSerializer

class SimpleSecureCookieSessionInterface(SecureCookieSessionInterface):
    def get_signing_serializer(self, secret_key):
        if not secret_key:
            return None
        signer_kwargs = dict(
            key_derivation=self.key_derivation,
            digest_method=self.digest_method
        )
        return URLSafeTimedSerializer(secret_key, salt=self.salt, serializer=self.serializer, signer_kwargs=signer_kwargs)

def decode_flask_cookie(secret_key, cookie):
    ssci = SimpleSecureCookieSessionInterface()
    signing_serializer = ssci.get_signing_serializer(secret_key)
    return signing_serializer.loads(cookie)

# 使用提供的 secret_key 和 cookie
secret_key = "thisisfake"
from flask.sessions import SecureCookieSessionInterface
from itsdangerous import URLSafeTimedSerializer

class SimpleSecureCookieSessionInterface(SecureCookieSessionInterface):
    def get_signing_serializer(self, secret_key):
        if not secret_key:
            return None
        signer_kwargs = dict(
            key_derivation=self.key_derivation,
            digest_method=self.digest_method
        )
        return URLSafeTimedSerializer(secret_key, salt=self.salt, serializer=self.serializer, signer_kwargs=signer_kwargs)

def decode_flask_cookie(secret_key, cookie):
    ssci = SimpleSecureCookieSessionInterface()
    signing_serializer = ssci.get_signing_serializer(secret_key)
    return signing_serializer.loads(cookie)

# 使用提供的 secret_key 和 cookie
secret_key = "ihfoajfdlngalskfnglnsljgaaskdhglmasdlglasdg"
# cookie = ".eJyrVsotTleyUvJIzcnJV6iuTs7PS8tMr63VUYCBkIzMYoXS4tSivMTcVIXM4jz1EoXUisziEh2F4nyFyvxShcSiVIX00tTiEiUdJZBCoHEQbi0AuvwfUg.ZZOA6w.8hrnEE3nRAzZpmGnIEU3M31WzR4"
cookie = "eyJ1c2VyIjoiZ3Vlc3QifQ.ZZOEcw.yFAg5QeL6AVwgOQrbjOHtV7RtSM"

# 解析 cookie
decoded_cookie = decode_flask_cookie(secret_key, cookie)
print(decoded_cookie)

