#!/bin/bash
# Generate self-signed SSL certificate for AIDP

CERT_DIR="/home/docker/AI-Code/ssl"
mkdir -p "$CERT_DIR"

echo "=== Generating Self-Signed SSL Certificate ==="

# Generate certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$CERT_DIR/aidp.key" \
    -out "$CERT_DIR/aidp.crt" \
    -subj "/C=CN/ST=State/L=City/O=AIDP/CN=192.168.0.100" \
    -addext "subjectAltName=IP:192.168.0.100,DNS:localhost"

echo "Certificate generated:"
echo "  Key:  $CERT_DIR/aidp.key"
echo "  Cert: $CERT_DIR/aidp.crt"

# Set permissions
chmod 600 "$CERT_DIR/aidp.key"
chmod 644 "$CERT_DIR/aidp.crt"

echo ""
echo "To use with uvicorn:"
echo "  uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile=$CERT_DIR/aidp.key --ssl-certfile=$CERT_DIR/aidp.crt"
