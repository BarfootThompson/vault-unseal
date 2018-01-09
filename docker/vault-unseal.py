import os
import sys
import json
import time
import logging
from pprint import pformat

import requests


VERSION = '0.1'
ENV_PREFIX = 'VU_'
CONFIG_FILENAME = 'vault-unseal.json'


def configure_logger():
    logging.basicConfig(stream=sys.stdout, format='[%(asctime)s] %(levelname)s:%(message)s')
    logger = logging.getLogger('vault-unseal')
    logger.setLevel(logging.DEBUG if 'VU_DEBUG' in os.environ else logging.INFO)
    return logger


def read_configuration_file(filename=CONFIG_FILENAME):
    try:
        with open(filename) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def read_setting(setting_name, parameters, is_optional, logger):
    if setting_name.endswith('*'):
        prefix = setting_name[:-1]
        setting = {key: value for key, value in parameters.items() if key.startswith(prefix)}
    else:
        setting = parameters.get(setting_name)

    if not setting and not is_optional:
        message = 'Error: %s is not specified. Specify it either in %s or as environment variable prefixed with %s'
        logger.error(message, setting_name, CONFIG_FILENAME, ENV_PREFIX)
        sys.exit(1)

    return setting


def unseal_vault(base_url, time_interval, unseal_keys, logger):
    url = f'{base_url}/v1/sys/seal-status'
    unseal_url = f'{base_url}/v1/sys/unseal'

    r = requests.get(url).json()
    logger.debug('%s', r)

    try:
        sealed = r['sealed']
    except KeyError:
        logger.error('Error: cannot find \'sealed\' in returned JSON\n%s', r)
    else:
        if sealed:
            logger.info('Detected sealed vault. Unsealing...')
            for key_name, key_value in unseal_keys.items():
                logger.debug('Using key %s (%s)', key_name, key_value)
                r = requests.put(unseal_url, json={'key': key_value}).json()
                if r['sealed']:
                    logger.debug('Unseal result: %s', r)
                else:
                    logger.info('Unsealed successfully')
                    break
            else:
                logger.error('Something went wrong, failed to unseal. Check the keys.\n%s', r)
                sys.exit(2)


def unseal_goldfish(base_url, vault_url, time_interval, goldfish_id, goldfish_secret, logger):
    url = f'{base_url}/v1/health'
    bootstrap_url = f'{base_url}/v1/bootstrap'
    loging_url = f'{vault_url}/v1/auth/approle/login'
    wrapped_url = f'{vault_url}/v1/auth/approle/role/goldfish/secret-id'

    r = requests.get(url).json()
    logger.debug('%s', r)

    try:
        bootstrapped = r['bootstrapped']
    except KeyError:
        logger.error('Error: cannot find \'bootstrapped\' in returned JSON\n%s', r)
    else:
        if not bootstrapped:
            try:
                logger.info('Detected non-bootrstrapped goldfish. Logging in to vault...')
                r = requests.post(loging_url,json={'role_id':goldfish_id,'secret_id':goldfish_secret}).json()            
                logger.debug('%s', r)
                token = r['auth']['client_token']
                logger.info('Getting bootstrap token from vault...')
                r = requests.post(wrapped_url,headers={'X-Vault-Wrap-TTL':'20','X-Vault-Token':token}).json()            
                logger.debug('%s', r)
                token = r['wrap_info']['token']
                logger.info('Bootstrapping goldfish...')
                r = requests.post(bootstrap_url,json={'wrapping_token':token}).json()            
                logger.debug('%s', r)
                if r['result'] == 'success':
                    logger.info('Bootstrapped successfully')
                else:
                    logger.error('Something went wrong, failed to bootstrap. Run with enironment VU_DEBUG=1 to get more info')
            except KeyError:
                logger.error('Error: cannot find expexted key in returned JSON\n%s', r)


def main():
    logger = configure_logger()
    logger.info('vault-unseal.py version %s', VERSION)
    logger.debug('Dumping environment block: \n%s', pformat(dict(os.environ)))

    # Filter environment variables of interest
    settings = {key[len(ENV_PREFIX):]: value for key, value in os.environ.items() if key.startswith(ENV_PREFIX)}
    # Update values with those found in configuration file
    settings.update(read_configuration_file())

    # Retrieve required parameters
    vault_url = read_setting('VAULT_URL', settings, False, logger)
    time_interval = int(read_setting('TIME_INTERVAL_SECONDS', settings, False, logger))
    unseal_keys = read_setting('UNSEAL_KEY_*', settings, True, logger)

    goldfish_url = read_setting('GOLDFISH_URL', settings, True, logger)
    goldfish_id = read_setting('GOLDFISH_ID', settings, True, logger)
    goldfish_secret = read_setting('GOLDFISH_SECRET', settings, True, logger)

    do_vault = bool(unseal_keys)
    do_goldfish = (goldfish_url and goldfish_id and goldfish_secret)
    if not do_vault and not do_goldfish:
        logger.error('You have not specified enough parameters to unseal either vault or goldfish')
        logger.error('For vault you must specify UNSEAL_KEY_*')
        logger.error('For goldfish you must specify GOLDFISH_URL, GOLDFISH_ID, GOLDFISH_SECRET')
        logger.error('If you pass them as environment variables remember to prefix them with VU_')
        sys.exit(3)

    logger.info('TIME_INTERVAL_SECONDS = %d', time_interval)
    logger.info('VAULT_URL = %s', vault_url)
    if do_vault:
        logger.info('Number of unseal keys: %d', len(unseal_keys))
        logger.debug('UNSEAL_KEYS:')
        for key, value in unseal_keys.items():
            logger.debug('- %s: %s', key, value)

    if do_goldfish:
        logger.info('GOLDFISH_URL = %s', goldfish_url)
        logger.info('GOLDFISH_ID = %s', goldfish_id)
        logger.debug('GOLDFISH_SECRET = %s', goldfish_secret)

    logger.info('If you do not see any output below, it means that the vault is contacted successfully and its unsealed')
    logger.info('Vault will be contacted every %d seconds', time_interval)
    logger.info('Run with environment variable VU_DEBUG set for debug output')

    while True:
        try:
            if do_vault:
                unseal_vault(vault_url, time_interval, unseal_keys, logger)
            if do_goldfish:
                unseal_goldfish(goldfish_url, vault_url, time_interval, goldfish_id, goldfish_secret, logger)
        except Exception:
            logger.exception('An exception occured:')
        time.sleep(time_interval)

if __name__ == '__main__':
    main()
