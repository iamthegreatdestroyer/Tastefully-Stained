#!/usr/bin/env bash
# =============================================================================
# generate_dev_certs.sh
# =============================================================================
# Generates a throwaway, DEVELOPMENT-ONLY X.509 certificate chain for
# signing C2PA manifests locally: a self-signed root CA, plus a leaf
# certificate issued by that CA (C2PA's signing-certificate profile does
# not accept a certificate that is self-signed directly -- it must be
# issued by a separate CA; see backend/watermark_engine/c2pa/README.md
# and the Phase 6 implementation notes for how this was discovered).
#
# THIS IS NOT A PRODUCTION CERTIFICATE. Nothing signed with it will be
# trusted by real-world C2PA verifiers (e.g. Adobe's Content Credentials
# Verify) because this dev CA is not in any public trust list. Sourcing a
# real, C2PA-recognized signing certificate is a separate business/legal
# enrollment process (see https://c2pa.org/specifications/) and is out of
# scope here.
#
# Output (all gitignored via the repo's existing *.pem / *.key patterns):
#   backend/certs/dev/ca.pem        - self-signed dev root CA cert (public)
#   backend/certs/dev/ca.key        - dev root CA private key (KEEP LOCAL)
#   backend/certs/dev/leaf.pem      - leaf signing cert, issued by ca.pem
#   backend/certs/dev/leaf.key      - leaf private key, PKCS#8 (KEEP LOCAL)
#   backend/certs/dev/fullchain.pem - leaf.pem + ca.pem concatenated
#                                     (this is what C2PA_CERTIFICATE_PATH
#                                     should point at: c2pa-python expects
#                                     the full chain, leaf first)
#
# Usage:
#   bash generate_dev_certs.sh [output_dir]
#
# Safe to re-run: it will NOT overwrite an existing chain unless you
# remove the output directory first, so re-running after the repo already
# has a working dev chain is a no-op (prevents accidentally invalidating
# already-signed test fixtures).
# =============================================================================
set -euo pipefail

OUT_DIR="${1:-backend/certs/dev}"

if [ -f "${OUT_DIR}/fullchain.pem" ] && [ -f "${OUT_DIR}/leaf.key" ]; then
    echo "Dev certificate chain already exists at ${OUT_DIR}, skipping generation."
    echo "(Delete ${OUT_DIR} first if you want to regenerate.)"
    exit 0
fi

mkdir -p "${OUT_DIR}"
cd "${OUT_DIR}"

echo "Generating self-signed dev root CA (EC P-256)..."
openssl ecparam -name prime256v1 -genkey -noout -out ca.key
openssl req -x509 -new -key ca.key -nodes -out ca.pem -days 3650 \
  -subj "/C=US/ST=Dev/L=Dev/O=Tastefully Stained Dev CA/OU=Dev/CN=Tastefully Stained Dev Root CA (DEV ONLY - NOT FOR PRODUCTION)" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"

echo "Generating leaf signing key + CSR (EC P-256)..."
openssl ecparam -name prime256v1 -genkey -noout -out leaf_sec1.key
# Convert to PKCS#8 -- c2pa-python's native signer path requires PKCS#8
# ("-----BEGIN PRIVATE KEY-----"), not SEC1 ("-----BEGIN EC PRIVATE
# KEY-----"), which is what openssl ecparam -genkey produces by default.
openssl pkcs8 -topk8 -nocrypt -in leaf_sec1.key -out leaf.key
rm -f leaf_sec1.key

openssl req -new -key leaf.key -out leaf.csr \
  -subj "/C=US/ST=Dev/L=Dev/O=Tastefully Stained/OU=Dev/CN=Tastefully Stained Dev Signer (DEV ONLY)"

cat > leaf_ext.cnf <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,nonRepudiation
extendedKeyUsage=critical,emailProtection
EOF

echo "Issuing leaf certificate from dev CA..."
openssl x509 -req -in leaf.csr -CA ca.pem -CAkey ca.key -CAcreateserial \
  -out leaf.pem -days 3650 -sha256 -extfile leaf_ext.cnf

cat leaf.pem ca.pem > fullchain.pem

rm -f leaf.csr leaf_ext.cnf ca.srl

chmod 600 ca.key leaf.key
chmod 644 ca.pem leaf.pem fullchain.pem

echo ""
echo "Dev certificate chain generated at ${OUT_DIR}/:"
ls -la .
echo ""
echo "C2PA_CERTIFICATE_PATH should point at: ${OUT_DIR}/fullchain.pem"
echo "C2PA_SIGNING_KEY_PATH should point at:  ${OUT_DIR}/leaf.key"
echo ""
echo "REMINDER: this is a development-only, self-signed chain. Manifests"
echo "signed with it will NOT validate against real-world C2PA verifiers."
