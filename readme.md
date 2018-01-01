# Automatic unseal for [vault](https://www.vaultproject.io/).

The scenario is when you do not care for manually unsealing your vault and want to unseal it whenever it comes online after restart automatically. Be warned that this is against all security practices, and some people even suggest that if you want automatic unseal you do not need vault.

This is a python script that you can run from a small docker container. The script takes three inputs:
- The url of vault you want to automatically unlock (e.g. https://vault.rocks)
- The number of seconds to sleep between checks if the vault is locked
- An array of unseal keys (you probably want a single key, since if you do not care for manual unsealing, it's unlikely that you created more than one)

The parameters can be provided either in vault-unseal.json:

```json
{
  "ADDRESS_URL" : "https://vault.test.bat.nz",
  "TIME_INTERVAL_SECONDS" : 10,
  "UNSEAL_KEY_1" : "mYxh8zruCmImx46Ccmqc9PWWh+Nuu/jPfxq7SPxtBesX",
  "UNSEAL_KEY_2" : "ewxM9/2rjvXviLHSaGv35XpEoNAHCmq7KcWHb4jDueOb",
  "UNSEAL_KEY_3" : "p17fGg/VmM7m6gL19g64MBJuL8wmbQb9bNeQTQm7fla3",
  "UNSEAL_KEY_4" : "OCiY/zTk6B7jtiiNuIYgr1wRBV87fdzHCkvPnw7+moOy",
  "UNSEAL_KEY_5" : "f5MpDx5ehgFbMLULpEBKSqZBiM7TQ6nIPMHwtXxYtECF"
}
```

Or then can be provided as environment variables with `VU_` prefix:

- VU_ADDRESS_URL=https://vault.test.bat.nz
- VU_TIME_INTERVAL_SECONDS=10
- VU_UNSEAL_KEY_1=mYxh8zruCmImx46Ccmqc9PWWh+Nuu/jPfxq7SPxtBesX
- VU_UNSEAL_KEY_2=ewxM9/2rjvXviLHSaGv35XpEoNAHCmq7KcWHb4jDueOb
- VU_UNSEAL_KEY_3=p17fGg/VmM7m6gL19g64MBJuL8wmbQb9bNeQTQm7fla3
- VU_UNSEAL_KEY_4=OCiY/zTk6B7jtiiNuIYgr1wRBV87fdzHCkvPnw7+moOy
- VU_UNSEAL_KEY_5=f5MpDx5ehgFbMLULpEBKSqZBiM7TQ6nIPMHwtXxYtECF

To build the docker container run in the docker subfolder of this repo:

```bash
docker build --no-cache -t andrewsav/vault-unseal .
docker push andrewsav/vault-unseal
```

To run the container, either use docker-compose.yml from this repo (edit it first), or run from command line:

```
docker run --name vault-unseal -dt -e VU_ADDRESS_URL=https://vault.test.bat.nz ... etc ... andrewsav/vault-unseal
```

Make sure to put the rest of `-e` parameters in.
