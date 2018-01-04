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


def read_setting(setting_name, parameters, logger):
    if setting_name.endswith('*'):
        prefix = setting_name[:-1]
        setting = {key: value for key, value in parameters.items() if key.startswith(prefix)}
    else:
        setting = parameters.get(setting_name)

    if not setting:
        message = 'Error: %s is not specified. Specify it either in %s or as environment variable prefixed with %s'
        logger.error(message, setting_name, CONFIG_FILENAME, ENV_PREFIX)
        sys.exit(1)

    return setting


def unseal(base_url, time_interval, unseal_keys, logger):
    url = f'{base_url}/v1/sys/seal-status'
    unseal_url = f'{base_url}/v1/sys/unseal'

    while True:
        try:
            r = requests.get(url).json()
            logger.debug('status: %s', r)

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
        except Exception:
            logger.exception('An exception occured:')
        time.sleep(time_interval)


def main():
    logger = configure_logger()
    logger.info('vault-unseal.py version %s', VERSION)
    logger.debug('Dumping environment block: \n%s', pformat(dict(os.environ)))

    # Filter environment variables of interest
    settings = {key[len(ENV_PREFIX):]: value for key, value in os.environ.items() if key.startswith(ENV_PREFIX)}
    # Update values with those found in configuration file
    settings.update(read_configuration_file())

    # Retrieve required parameters
    address_url = read_setting('ADDRESS_URL', settings, logger)
    time_interval = int(read_setting('TIME_INTERVAL_SECONDS', settings, logger))
    unseal_keys = read_setting('UNSEAL_KEY_*', settings, logger)

    logger.info('ADDRESS_URL = %s', address_url)
    logger.info('TIME_INTERVAL_SECONDS = %d', time_interval)
    logger.info('Number of unseal keys: %d', len(unseal_keys))
    logger.debug('UNSEAL_KEYS:')
    for key, value in unseal_keys.items():
        logger.debug('- %s: %s', key, value)

    logger.info('If you do not see any output below, it means that the vault is contacted successfully and its unsealed')
    logger.info('Vault will be contacted every %d seconds', time_interval)
    logger.info('Run with environment variable VU_DEBUG set for debug output')

    unseal(address_url, time_interval, unseal_keys, logger)


if __name__ == '__main__':
    main()
