# HappyLBR

Goal: automate LBR VIP configuration

Main features:

* Allocate ip address in RT/Netbox and set it as shared ip for target server
* Create Virtual Server at F5/A10
* Update relevant DNS record

## Principles and key decisions

* Failures should be raised as exceptions up to CLI/UI level
* For most failures we expect "global" retry at CLI/UI level
* Global retry should recreate objects based on patch methods (diff - delete - create)
* Caching must be avoided to make sure that the retry sees actual state of the system

## Usage

See happyvip.py -h for options

### Examples

    Create mandatory entrypoints for lab-lem-ams:
    python happyvip.py create lab-lem-ams

    Create specific entrypoints:
    python happyvip.py create lab-lem-ams --entrypoints intapi

    Create all entrypoints related to service pwr for lab-lem-ams:
    python happyvip.py create lab-lem-ams --services pwr

    Delete all entrypoints:
    python happyvip.py delete lab-lem-ams --all

    Delete specific entrypoints:
    python happyvip.py delete lab-lem-ams --entrypoints intapi,api

    Delete all entrypoints related to service psr for lab-lem-ams:
    python happyvip.py delete lab-lem-ams --services psr

## How to contribute

* Please comply with:
```
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=128 --statistics --ignore=E402
```
* Write tests for your code (we use pytest for testing)
* Run tests locally before pushing
```
python -m pytest tests/test_*.py
```
