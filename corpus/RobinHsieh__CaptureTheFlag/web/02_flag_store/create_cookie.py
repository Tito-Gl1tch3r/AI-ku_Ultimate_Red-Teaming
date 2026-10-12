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

def encode_flask_cookie(secret_key, session):
    ssci = SimpleSecureCookieSessionInterface()
    signing_serializer = ssci.get_signing_serializer(secret_key)
    return signing_serializer.dumps(session)

# 使用提供的 secret_key 和要设置的 session 数据
secret_key = "ihfoajfdlngalskfnglnsljgaaskdhglmasdlglasdg"
session_data = {'user': '1mv32yv32y21ch'}

# 生成 cookie
encoded_cookie = encode_flask_cookie(secret_key, session_data)
print(encoded_cookie)
