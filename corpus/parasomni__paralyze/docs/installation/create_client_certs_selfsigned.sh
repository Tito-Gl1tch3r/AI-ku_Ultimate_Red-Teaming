#!/bin/bash
set -e

if [ $# -ne 2 ]; then
  echo "Usage: $0 <server_id> <number_of_clients>"
  exit 1
fi

SERVER_ID="$1"
NUM_CLIENTS="$2"

SERVER_DIR="pki/servers/$SERVER_ID"
SERVER_KEY="$SERVER_DIR/server_private.key"
SERVER_CERT="$SERVER_DIR/server_cert.crt"

if [ ! -f "$SERVER_KEY" ] || [ ! -f "$SERVER_CERT" ]; then
  echo "[!] Server $SERVER_ID not found in $SERVER_DIR"
  exit 1
fi

for i in $(seq 1 "$NUM_CLIENTS"); do
  CLIENT_NAME="client$i"
  CLIENT_DIR="pki/clients/$SERVER_ID/$CLIENT_NAME"
  mkdir -p "$CLIENT_DIR"

  echo "[*] Generating key for $CLIENT_NAME..."
  openssl ecparam -name prime256v1 -genkey -noout -out "$CLIENT_DIR/cs_private.key"

  echo "[*] Creating CSR for $CLIENT_NAME..."
  openssl req -new -key "$CLIENT_DIR/cs_private.key" -out "$CLIENT_DIR/$CLIENT_NAME.csr" \
    -subj "/C=US/ST=CA/L=Internal/O=PKI/OU=Client/CN=$CLIENT_NAME.local"

  cat > "$CLIENT_DIR/$CLIENT_NAME.conf" <<EOF
[ v3_req ]
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyAgreement
extendedKeyUsage = clientAuth
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = $CLIENT_NAME.local
EOF

  echo "[*] Signing client certificate $CLIENT_NAME with server $SERVER_ID..."
  openssl x509 -req \
    -in "$CLIENT_DIR/$CLIENT_NAME.csr" \
    -CA "$SERVER_CERT" \
    -CAkey "$SERVER_KEY" \
    -CAcreateserial \
    -out "$CLIENT_DIR/client_cert.crt" \
    -days 825 -sha256 \
    -extensions v3_req -extfile "$CLIENT_DIR/$CLIENT_NAME.conf"

  cat "$CLIENT_DIR/client_cert.crt" "$SERVER_CERT" > "$CLIENT_DIR/cs.chain.crt"
  echo "[✓] Client certificate $CLIENT_NAME created with chain."
done
