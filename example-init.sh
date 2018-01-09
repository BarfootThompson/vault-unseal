#!/bin/bash

###
# Read settings
###

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"
SETTINGS="$SCRIPTPATH/settings.sh"

if [ ! -f $SETTINGS ]; then
  echo "Please create settings.sh from the template in the URL above"
  echo "https://github.com/AndrewSav/test-vault/blob/master/settings.sh.template"
  exit 1
fi

source $SETTINGS

echo "Vault: $VAULT"
echo "Goldfish: $GOLDFISH"

###
# Check vault status
###

status=$(curl -s -w '%{http_code}' -o ~result.json  https://$VAULT/v1/sys/init)
if [ $status -ne 200 ]; then
  echo "Error: Failed getting vault init status. Code: $status"
  cat ~result.json
  rm -f ~result.json
  exit 2
fi

if ! INITIALIZED=$(jq -r ".initialized" ~result.json); then
  echo "Error: Failed to parse json result"
  cat ~result.json
  rm -f ~result.json
  exit 3
fi 

if [[ $INITIALIZED != false && $INITIALIZED != true ]]; then
  echo "Error: Expected initialized status to be true or false, got $INITIALIZED"
  cat ~result.json
  rm -f ~result.json
  exit 4
fi
rm -f ~result.json

if [[ $INITIALIZED = true ]]; then
  echo "Error: This vault is already initialized!"
  exit 5
fi

###
# Initialize vault
###

data='{"secret_shares":5,"secret_threshold":3}'

status=$(curl -s -w '%{http_code}' -X PUT --data "$data" -o ~result.json  https://$VAULT/v1/sys/init)
if [ $status -ne 200 ]; then
  echo "Error: Failed getting vault init status. Code: $status"
  cat ~result.json
  rm -f ~result.json
  exit 6
fi

if ! KEYS=$(jq -r ".keys_base64[]" ~result.json); then
  echo "Error: Failed to parse json result"
  cat ~result.json
  rm -f ~result.json
  exit 7
fi 

echo -e "Your unseal Keys:\n$KEYS"

if ! ROOT=$(jq -r ".root_token" ~result.json); then
  echo "Error: Failed to parse json result"
  cat ~result.json
  rm -f ~result.json
  exit 8
fi 

echo "Your token: $ROOT"

VAULT_ADDR="https://$VAULT"
VAULT_TOKEN=$ROOT

set -e

###
# Goldfish setup in vault
###

#One place for curl options
CURL_OPT="-s -H X-Vault-Token:${VAULT_TOKEN}"

# unseal vault
for KEY in $KEYS; do
  curl ${CURL_OPT} -X PUT ${VAULT_ADDR}/v1/sys/unseal -d "{\"key\":\"$KEY\"}"
done

# transit backend and approle auth backend need to be enabled
curl ${CURL_OPT} ${VAULT_ADDR}/v1/sys/mounts/transit -d '{"type":"transit"}'
curl ${CURL_OPT} ${VAULT_ADDR}/v1/sys/auth/approle -d '{"type":"approle"}'

# see the policy file for details
curl ${CURL_OPT} -X PUT ${VAULT_ADDR}/v1/sys/policy/goldfish -d '{"policy": "path \"transit/encrypt/goldfish\" {capabilities = [\"read\",\"update\"]}, path \"transit/decrypt/goldfish\" {capabilities = [\"read\",\"update\"]}, path \"secret/goldfish*\" {capabilities = [\"read\",\"update\"]}"}'
curl ${CURL_OPT} ${VAULT_ADDR}/v1/auth/approle/role/goldfish -d '{"policies":"default,goldfish", "secret_id_num_uses":"1", "secret_id_ttl":"5", "period":"24h"}'
curl ${CURL_OPT} ${VAULT_ADDR}/v1/auth/approle/role/goldfish/role-id -d '{"role_id":"goldfish"}'

# initialize transit key. This is not strictly required but is proper procedure
curl ${CURL_OPT} -X POST ${VAULT_ADDR}/v1/transit/keys/goldfish

# production goldfish needs a generic secret endpoint to hot reload settings from. See Configuration page for details
curl ${CURL_OPT} ${VAULT_ADDR}/v1/secret/goldfish -d '{"DefaultSecretPath":"secret/", "TransitBackend":"transit", "UserTransitKey":"usertransit", "ServerTransitKey":"goldfish", "BulletinPath":"secret/bulletins/"}'

###
# For automatic goldfish automatic bootstrap
###

curl ${CURL_OPT} -X PUT ${VAULT_ADDR}/v1/sys/policy/goldfishapp -d '{"policy": "path \"auth/approle/role/goldfish/secret-id\" {capabilities = [\"create\",\"update\"]}"}'
curl ${CURL_OPT} ${VAULT_ADDR}/v1/auth/approle/role/goldfishapp -d '{"policies":"default,goldfishapp", "token_ttl":"5", "token_max_ttl":"5"}'

GOLDFISH_ID=`curl ${CURL_OPT} ${VAULT_ADDR}/v1/auth/approle/role/goldfishapp/role-id | jq -r ".data.role_id"`
GOLDFISH_SECRET=`curl ${CURL_OPT} -X POST ${VAULT_ADDR}/v1/auth/approle/role/goldfishapp/secret-id | jq -r ".data.secret_id"`
curl ${CURL_OPT} ${VAULT_ADDR}/v1/auth/approle/role/goldfishapp/role-id -d "{\"role_id\":\"$GOLDFISH_ID\"}"

###
# Dump json with the installation parameters
# This json can be then used as vault-unseal.json 
# ROOT_TOKEN is informational only and is not used
###

{
  cat <<- EOF
{
  "TIME_INTERVAL_SECONDS" : 10,
  "VAULT_URL" : "https://$VAULT",
EOF

  for KEY in $KEYS; do
    printf '  "UNSEAL_KEY_%u" : "%s",\n' $[++N] "$KEY"
  done

  cat <<- EOF
  "ROOT_TOKEN" :  "$ROOT",
  "GOLDFISH_URL" : "https://$GOLDFISH",
  "GOLDFISH_ID" :  "$GOLDFISH_ID",
  "GOLDFISH_SECRET" : "$GOLDFISH_SECRET"
}
EOF
} > example-init.json

#cat example-init.json
#curl ${CURL_OPT} --header "X-Vault-Wrap-TTL: 20" -X POST ${VAULT_ADDR}/v1/auth/approle/role/goldfish/secret-id
