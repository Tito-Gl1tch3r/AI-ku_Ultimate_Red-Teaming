#!/bin/bash
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <number_of_servers>"
  exit 1
fi

NUM_SERVERS="$1"

for i in $(seq 1 "$NUM_SERVERS"); do
  NAME="server$i"
  DIR="pki/servers/$NAME"
  mkdir -p "$DIR"

  echo "[*] Creating dh file for $NAME..."
  openssl dhparam -out "$DIR/dh.pem" 2048

  echo "[*] Generating key for $NAME..."
  openssl ecparam -name prime256v1 -genkey -noout -out "$DIR/server_private.key"

  echo "[*] Creating CSR for $NAME..."
  openssl req -new -key "$DIR/server_private.key" -out "$DIR/$NAME.csr" \
    -subj "/C=US/ST=CA/L=Internal/O=PKI/OU=Server/CN=$NAME.local"

  cat > "$DIR/$NAME.conf" <<EOF
[ v3_ca ]
basicConstraints = CA:TRUE
keyUsage = digitalSignature, keyCertSign
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[ alt_names ]
DNS.1 = $NAME.local
EOF

  echo "[*] Signing $NAME with Root CA..."
  openssl x509 -req \
    -in "$DIR/$NAME.csr" \
    -CA pki/root/root.crt \
    -CAkey pki/root/root.key \
    -CAserial pki/root/root.srl \
    -out "$DIR/server_cert.crt" \
    -days 825 -sha256 \
    -extensions v3_ca -extfile "$DIR/$NAME.conf"

  cat "$DIR/server_cert.crt" pki/root/root.crt > "$DIR/server.chain.crt"

  echo "[✓] $NAME certificate and chain created."
done
