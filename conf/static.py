healthchecks = {
    "A10": {
        "default": "tcp"
    },
    "F5": {
        "default": "tcp"
    },
}

balancers = {
    "AMS02": {
        "A10": {
            "address": "a10.mydomain",
            "network": "10.0.0.0",
            "prefix": "19",
        },
        "F5": {
            "address": "f5.mydomain",
            "network": "10.1.0.0",
            "prefix": "19",
            "partition": "ams-up",
        },
    },
}

shared_entrypoints = {
    "service": {}
}

entrypoints = {
    "api": {
        "LB": "A10",
        "mandatory": True,
        "service": "pwr",
        "ports": [
            {
                "port": 443,
                "target_port": 80,
                "protocol": "https",
                "template_http": "rc-xffxfp-https"
            },
            {
                "port": 80,
                "target_port": 80,
                "protocol": "http",
                "template_http": "rc-xffxfp-http"
            }
        ],
    },
    "intapi": {
        "LB": "A10",
        "mandatory": True,
        "service": "pwr",
        "ports": [
            {
                "port": 443,
                "target_port": 8082,
                "protocol": "https",
                "template_http": "rc-xffxfp-https"
            },
            {
                "port": 80,
                "target_port": 8082,
                "protocol": "http",
                "template_http": "rc-xffxfp-http"
            }
        ]
    }
}
