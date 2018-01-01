import os
import sys
import json
import time
import datetime
from pprint import pprint
import requests

version = "0.1"
envPrefix = "VU_"
config = "vault-unseal.json"

def PrintWithTimestamp(string):
  timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
  sys.stdout.write(f"[{timestamp}] {string}\n")

def PrintDebug(string):
  if "VU_DEBUG" in os.environ:
    PrintWithTimestamp(f"DEBUG: {string}")

def PrintParameterError(name):
  PrintWithTimestamp(f"Error: {name} is not specified. Specify it either in {config} file, or as enviroment variable prefixed with {envPrefix}")

def NormalizePrefix(name, string):
  return name + string[len(envPrefix+name):]

def ReadSingleSetting(name):
  result = None
  try:
    with open(config) as data_file:    
      data = json.load(data_file)
    result = data[name]
  except (FileNotFoundError, KeyError):
    pass
  if envPrefix+name in os.environ:
    result = os.environ[envPrefix+name]
  return result
    

def ReadMultiSetting(name):
  result = None
  try:
    with open(config) as data_file:    
      data = json.load(data_file)
    result = { key:data[key] for key in filter(lambda x: x.startswith(name), data.keys()) }
  except (FileNotFoundError):
    pass

  result = result if result else {}
  
  prefix = envPrefix + name
  envResult = { NormalizePrefix(name,key):os.environ[key] for key in filter(lambda x: x.lower().startswith(prefix.lower()), list(os.environ.keys())) }

  finalResult = list({**result,**envResult}.values())
  finalResult = finalResult if len(finalResult) else None
  return finalResult

def ReadSetting(name):
  if name.endswith("*"):
    return ReadMultiSetting(name[0:-1])
  else:
    return ReadSingleSetting(name)   

PrintWithTimestamp(f"vault-unseal.py version {version}")

if "VU_DEBUG" in os.environ:
  PrintDebug("Dumping environment block:")
  pprint(dict(os.environ))

addressUrl = ReadSetting("ADDRESS_URL")
timeIntervalSeconds = int(ReadSetting("TIME_INTERVAL_SECONDS"))
unsealKeys = ReadSetting("UNSEAL_KEY_*")

if not addressUrl:
  PrintParameterError("ADDRESS_URL")
  sys.exit(1)

if not timeIntervalSeconds:
  PrintParameterError("TIME_INTERVAL_SECONDS")
  sys.exit(1)

if not unsealKeys:
  PrintParameterError("UNSEAL_KEY_*")
  sys.exit(1)

PrintWithTimestamp(f"ADDRESS_URL = {addressUrl}")
PrintWithTimestamp(f"TIME_INTERVAL_SECONDS = {timeIntervalSeconds}")
PrintWithTimestamp("Number of unseal keys: " + str(len(unsealKeys)))

PrintDebug("UNSEAL_KEYS:")
for key in unsealKeys:
  PrintDebug(f"- {key}")
PrintWithTimestamp("If you do not see any output below, it means that the vault is contacted successfully and its unsealed")
PrintWithTimestamp(f"Vault will be contacted every {timeIntervalSeconds} seconds")
PrintWithTimestamp("Run with environment variable VU_DEBUG set to 1 for debug output")

while True:
  try:
    r = requests.get(f"{addressUrl}/v1/sys/seal-status").json()
    PrintDebug(f"status:{r}")
    if "sealed" in r:
      if r["sealed"] == True:
        PrintWithTimestamp("Detected sealed vault. Unsealing...")
        for key in unsealKeys:
          PrintDebug(f"key:{key}")
          r = requests.put(f"{addressUrl}/v1/sys/unseal", json = {"key":key}).json()
          PrintDebug(f"unseal:{r}")
        if r["sealed"] == True:
          PrintWithTimestamp("something went wrong, failed to unseal. Check the keys")
          PrintWithTimestamp(r)
          sys.exit(2)
        else:
          PrintWithTimestamp("Unsealed successfully")
    else:
      PrintWithTimestamp("Error: cannot find 'sealed' in returned json")
      pprint(r)
  except Exception as e:
    PrintWithTimestamp(f"Exception:{e}")
    PrintWithTimestamp(type(e))
    pprint(vars(e))
  time.sleep(timeIntervalSeconds)  
