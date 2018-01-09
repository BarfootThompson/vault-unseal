# Automatic unseal for [vault](https://www.vaultproject.io/) and automatic bootstrap for [goldfish](https://github.com/Caiyeon/goldfish)

## Vault
The scenario is when you do not care for manually unsealing your vault and want to unseal it whenever it comes online after restart automatically. Be warned that this is against all security practices, and some people even suggest that if you want automatic unseal you do not need vault.

This is a python script that you can run from a small docker container. The script takes three inputs:
- The url of vault you want to automatically unlock (e.g. https://vault.rocks)
- The number of seconds to sleep between checks if the vault is locked
- An array of unseal keys (you probably want a single key, since if you do not care for manual unsealing, it's unlikely that you created more than one)

The parameters can be provided either in vault-unseal.json:

```json
{
  "VAULT_URL" : "https://vault.test.bat.nz",
  "TIME_INTERVAL_SECONDS" : 10,
  "UNSEAL_KEY_1" : "mYxh8zruCmImx46Ccmqc9PWWh+Nuu/jPfxq7SPxtBesX",
  "UNSEAL_KEY_2" : "ewxM9/2rjvXviLHSaGv35XpEoNAHCmq7KcWHb4jDueOb",
  "UNSEAL_KEY_3" : "p17fGg/VmM7m6gL19g64MBJuL8wmbQb9bNeQTQm7fla3",
  "UNSEAL_KEY_4" : "OCiY/zTk6B7jtiiNuIYgr1wRBV87fdzHCkvPnw7+moOy",
  "UNSEAL_KEY_5" : "f5MpDx5ehgFbMLULpEBKSqZBiM7TQ6nIPMHwtXxYtECF"
}
```

Or then can be provided as environment variables with `VU_` prefix:

- VU_VAULT_URL=https://vault.test.bat.nz
- VU_TIME_INTERVAL_SECONDS=10
- VU_UNSEAL_KEY_1=mYxh8zruCmImx46Ccmqc9PWWh+Nuu/jPfxq7SPxtBesX
- VU_UNSEAL_KEY_2=ewxM9/2rjvXviLHSaGv35XpEoNAHCmq7KcWHb4jDueOb
- VU_UNSEAL_KEY_3=p17fGg/VmM7m6gL19g64MBJuL8wmbQb9bNeQTQm7fla3
- VU_UNSEAL_KEY_4=OCiY/zTk6B7jtiiNuIYgr1wRBV87fdzHCkvPnw7+moOy
- VU_UNSEAL_KEY_5=f5MpDx5ehgFbMLULpEBKSqZBiM7TQ6nIPMHwtXxYtECF

To build the docker container run in the docker subfolder of this repo:

```bash
docker build --no-cache -t andrewsav/vault-unseal .
```

To run the container, either use docker-compose.yml from this repo (edit it first), or run from command line:

```
docker run --name vault-unseal -dt -e VU_VAULT_URL=https://vault.test.bat.nz ... etc ... andrewsav/vault-unseal
```

Make sure to put the rest of `-e` parameters in. To make it less unwieldy you can use `docker-compose.yml` sample proived to start the container with docker-compose.

## Goldfish

Similarily to the above the script can bootstrap Goldfish. Make sure to include the following parameters

```json
{
  "TIME_INTERVAL_SECONDS" : 10,
  "VAULT_URL" : "https://vault.test.bat.nz",
  "GOLDFISH_URL" : "https://goldfish.test.bat.nz",
  "GOLDFISH_ID" :  "3565857e-840d-0ede-9e72-a61cf57676bf",
  "GOLDFISH_SECRET" : "451252f4-56ab-ad69-b827-f6a648ea6c77"
}
```

Same as before, you can either include these in a json file or as environment variables prefixed with `VU_`.


`GOLDFISH_ID` and `GOLDFISH_SECRET` is a `role_id` and a `secret_id` of an approle that you must setup, that can access `/auth/approle/role/goldfish/secret-id` to get goldfish wrapped token for bootstrap.
Here is a sample policy:

```hcl
path "auth/approle/role/goldfish/secret-id" {
   capabilities = ["create", "update"]
}
```

You can write it to vault with `vault policy-write goldfishapp goldfishapp.hcl` where `goldfishapp.hcl` is the file name with your policy. Here is how you can create the requried approle:

```
vault write auth/approle/role/goldfishapp token_ttl=5m token_max_ttl=5m policies=goldfishapp # consider using bound_cidr_list=1.1.1.1
gold_role=$(vault read -field=role_id auth/approle/role/goldfishapp/role-id)
gold_secret=$(vault write -field=secret_id -f auth/approle/role/goldfishapp/secret-id)
vault write auth/approle/role/goldfishapp/role-id role_id=$gold_role
echo "goldfish role_id: $gold_role"
echo "goldfish secret_id: $gold_secret"
````

You will use these as `GOLDFISH_ID` and `GOLDFISH_SECRET` above. If a check indicates that goldfish is not bootstrapped, the automatic bootstrap script then will:

- Login to vault with these `role_id` and `secret_id` and obtain vault token
- Read wrapped bootstrap token from vault with the token generated on the previous step
- Bootstrap goldfish with the obtained token

## Example setup

There is `example-init.sh` bash script supplied, make sure you have `jq` and `curl` before you run it.

The script is to set up a test vault/goldfish instances in a "prodction-like" manner. First setup fresh unitialized vault and get goldfish up and running.
One way of doing this is using [vault](https://hub.docker.com/_/vault/) and [goldfish](https://hub.docker.com/r/andrewsav/goldfish/) docker images and [traefic](https://traefik.io) 
for TLS certificates via [Let's Encrypt](https://letsencrypt.org) integration. If you have a domain name that you can point to your test machine ip,
you can set this up by using [this repo](https://github.com/AndrewSav/test-vault).

Prepare a `settings.sh` file similar to [this one](https://github.com/AndrewSav/test-vault/blob/master/settings.sh.template) (you don't require `EMAIL` in it). 
You might want to review the body of the `example-init.sh` to make sure that initialization and setup of vault and goldfish is done for you liking. 
For goldfish recommended parameters are used and for vault, it's initialized with 5 keys and 3 shares.

The script then generate `example-init.json` that can be used as `vault-unseal.json`. The `ROOT_TOKEN` parameter in this json is informational and not used.

Once you've got generated `vault-unseal.json` you can use it to test your new installation with the Automatic unseal/bootstrap script.

In addition the example script generates a `docker-compose-example.yml` that you can use for using `docker-compose` to bring up the container with the unseal/bootstrap script.
