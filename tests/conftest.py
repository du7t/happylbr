import pytest


@pytest.fixture(scope="module")
def dns_data() -> dict:
    data = {
        "action": "add",
        "record_type": "A",
        "source": "testy-record.mydomain",
        "value": "192.168.33.44",
        "ttl": 300,
        "force": True,
        "ptr": False
    }
    return data


@pytest.fixture(scope="module")
def lbr_data() -> dict:
    data = {
        "node1": "lem01-t01-gpr01",
        "address1": "10.61.16.26",
        "pool1": "lem01-t01-gpr_8080",
        "node1_port1": 3333,
        "node1_port2": 22,
        "member1": "lem01-t01-gpr01:3333",
        "member2": "lem01-t01-gpr01:22",
        "virtual1": "gpr-lablemams_443",
        "virtual1_a10": "gpr-lablemams",
        "destination1": "10.62.9.123",
        "port1": 443,
        "protocol1": "https",
        "protocol2": "http",
        "port2": 80,
        "http_profile": "rc-xffxfp-https",
        "cert": "star.mydomain"
    }
    return data
