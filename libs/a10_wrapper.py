"""A10 acos client wrapper"""
import acos_client as acos
from acos_client.errors import AddressSpecifiedIsInUse
from acos_client.errors import NotFound
from acos_client.v30.responses import RESPONSE_CODES


class A10Manager:
    def __init__(
        self, address: str, user: str, password: str, partition: str = None
    ) -> None:
        self.mgmt = acos.Client(address, acos.AXAPI_30, user, password)
        self._servers = None
        self._groups = None
        self._virtuals = None
        self.partition = partition
        self._extend_responses()

    @property
    def servers(self) -> list[dict]:
        """Returns:
        [{
            'name': 'lem01-t01-psr01',
            'host': '10.61.101.133',
            ...
        }, ...]
        """
        if not self._servers:
            self._servers = self.mgmt.slb.server.get_all()["server-list"]
        return self._servers

    @property
    def groups(self) -> list[dict]:
        """Returns:
        [{
            'name': 'ac-amrstbams',
            'ip-address': '10.62.9.202',
            ...
        }, ...]
        """
        if not self._groups:
            self._groups = self.mgmt.slb.service_group.all()["service-group-list"]
        return self._groups

    @property
    def virtuals(self) -> list[dict]:
        """Returns:
        [{
            'name': 'ac-amrstbams',
            'ip-address': '10.62.9.202',
            ...
        }, ...]
        """
        if not self._virtuals:
            self._virtuals = self.mgmt.slb.virtual_server.all()["virtual-server-list"]
        return self._virtuals

    @staticmethod
    def refresh_on_change(data_type):
        def decorator(method):
            def wrapper(self, *args, **kwargs):
                result = method(self, *args, **kwargs)
                self._reset_data(data_type)
                return result

            return wrapper

        return decorator

    def _reset_data(self, data_type):
        if data_type == "server":
            self._servers = None
        elif data_type == "group":
            self._groups = None
        elif data_type == "virtual":
            self._virtuals = None

    # Servers
    def get_server(self, name: str) -> dict:
        """Returns:
        {
            'name': 'lem01-t01-psr01',
            'host': '10.61.101.133',
            'action': 'enable',
            ...
            'port-list': [{'port-number': 80,
                           'protocol': 'tcp',
                            ...
                        }, ...]
        }
        """
        try:
            return self.mgmt.slb.server.get(name=name)["server"]
        except NotFound:
            return {}

    def get_server_ip(self, name: str) -> str:
        return self.get_server(name=name).get("host")

    def get_server_by_ip(self, ip: str) -> dict:
        for server in self.servers:
            if server.get("host") == ip:
                return server

    def get_server_references(self, name: str) -> set[str]:
        used_in_groups = set()
        for group in self.groups:
            for member in group.get("member-list", []):
                if member.get("name") == name:
                    used_in_groups.add(group["name"])
        return used_in_groups

    @refresh_on_change(data_type="server")
    def create_server(self, name: str, ip: str, port_list: list[dict] = None) -> dict:
        """Args:
         port_list: [{"port-number": int / str, "protocol": "tcp" / "udp"}, ...]
        Returns:
         same as get_server
        """
        return self.mgmt.slb.server.create(
            name=name, ip_address=ip, port_list=port_list
        )["server"]

    @refresh_on_change(data_type="server")
    def delete_server(self, name: str) -> dict:
        """Returns:
        {'status': 'OK'}
        """
        return self.mgmt.slb.server.delete(name=name)["response"]

    # Service groups
    def get_group(self, name: str) -> dict:
        """Returns:
        {
            'name': 'lem01-t01-pwr_8082',
            'protocol': 'tcp',
            'health-check': 'http_pwr',
            ...
            'member-list': [{'name': "lem01-t01-pwr01",
                             'port': 8082,
                              ...
                        }, ...]
        }
        """
        try:
            return self.mgmt.slb.service_group.get(name=name)["service-group"]
        except NotFound:
            return {}

    def get_group_members_names(self, name: str) -> list[str]:
        members = self.get_group(name=name).get("member-list", [])
        return list({member["name"] for member in members})

    def get_group_references(self, name: str) -> set[str]:
        used_in_virtuals = set()
        for virtual in self.virtuals:
            for port in virtual.get("port-list", []):
                if port.get("service-group") == name:
                    used_in_virtuals.add(virtual["name"])
        return used_in_virtuals

    @refresh_on_change(data_type="group")
    def create_group(
        self, name: str, members: list[dict] = None, health_check: str = "tcp"
    ) -> dict:
        """Args:
         members: [{"name": str, "port": int / str}, ...]
        Returns:
         same as get_group
        """
        return self.mgmt.slb.service_group.create(
            name=name, mem_list=members, hm_name=health_check
        )["service-group"]

    @refresh_on_change(data_type="group")
    def delete_group(self, name: str) -> dict:
        """Returns:
        {'status': 'OK'}
        """
        return self.mgmt.slb.service_group.delete(name=name)["response"]

    # Virtual Servers and ports
    def get_virtual_server(self, name: str) -> dict:
        """Returns:
        {
            'name': 'api-lablemams',
            'ip-address': '10.62.9.123',
            'enable-disable-action': 'enable',
            ...
            'port-list': [{'port-number': "443",
                           'protocol': "https",
                           'service-group': 'lem01-t01-gpr_8080'
                              ...
                        }, ...]
        }
        """
        try:
            return self.mgmt.slb.virtual_server.get(name=name)["virtual-server"]
        except NotFound:
            return {}

    def get_virtual_server_by_ip(self, ip: str) -> dict:
        for virtual in self.virtuals:
            if virtual.get("ip-address") == ip:
                return virtual
        return {}

    def get_virtual_server_ip(self, name: str) -> str:
        return self.get_virtual_server(name=name).get("ip-address")

    def get_virtual_server_groups(self, name: str) -> list[str]:
        ports = self.get_virtual_server(name=name).get("port-list", [])
        return list(
            {port["service-group"] for port in ports if "service-group" in port}
        )

    def get_virtual_server_oper(self, name: str) -> dict:
        """Returns:
        {
            'oper': {
                'mac': '021f:a004:0002',
                'state': 'Functional Up',
                'ip-address': '10.62.10.125',
                ...
            },
            'port-list': [
                {
                    'oper': {
                        'state': 'All Up',
                        ...
                    },
                    'port-number': 80,
                    'protocol': 'http'
                },
                ...
            ],
            ...
        }
        """
        return self.mgmt.slb.virtual_server.oper(name=name)["virtual-server"]

    def get_virtual_server_state(self, name: str) -> str:
        """Returns:
        str: All Up / Functional Up / Partial Up / Down
        """
        return self.mgmt.slb.virtual_server.oper(name=name)["virtual-server"]["oper"][
            "state"
        ]

    @refresh_on_change(data_type="virtual")
    def create_virtual_server(
        self, name: str, ip: str, port_list: list[dict] = None
    ) -> dict:
        """Args:
         port_list: [{'port-number': int / str, 'service-group': str,
                      'protocol': str, 'use-rcv-hop-for-resp': 1, 'auto': 1,
                      'template-http': str, 'template-client-ssl': str}, ...]
        Returns:
         same as get_virtual_server
        """
        return self.mgmt.slb.virtual_server.create(
            name=name, ip_address=ip, port_list=port_list
        )["virtual-server"]

    @refresh_on_change(data_type="virtual")
    def delete_virtual_server(self, name: str) -> dict:
        """Returns:
        {'status': 'OK' / 'fail', 'err': {'msg': 'Object slb virtual-server {gpr-lablemams} does not exist'}}
        """
        return self.mgmt.slb.virtual_server.delete(name=name)["response"]

    def get_virtual_port(self, virtual_server: str, port: str, protocol: str) -> dict:
        """Returns:
        {
            'port-number': 443,
            'protocol': 'https',
            'service-group': 'lem01-t01-pwr_8082',
            'template-http': 'rc-xffxfp-https',
            'template-client-ssl': 'star.mydomain',
            'name': 'intapi-lablemams:443@lem01-t01-pwr_8082',
            ...
        }
        """
        try:
            return self.mgmt.slb.virtual_server.vport.get(
                virtual_server_name=virtual_server,
                port=port,
                protocol=protocol,
                name=None,
            )["port"]
        except NotFound:
            return {}

    @refresh_on_change(data_type="virtual")
    def create_virtual_port(
        self,
        virtual_server: str,
        port: str,
        protocol: str,
        group: str,
        template_http: str = None,
        client_ssl: str = None,
    ) -> dict:
        autosnat = 1
        use_rcv_hop = 1
        name = f"{virtual_server}:{port}@{group}"
        virtual_port_templates = {"template-http": template_http}
        return self.mgmt.slb.virtual_server.vport.create(
            virtual_server_name=virtual_server,
            protocol_port=port,
            protocol=protocol,
            name=name,
            service_group_name=group,
            autosnat=autosnat,
            use_rcv_hop=use_rcv_hop,
            virtual_port_templates=virtual_port_templates,
            template_client_ssl=client_ssl,
        )["port"]

    @refresh_on_change(data_type="virtual")
    def delete_virtual_port(
        self, virtual_server: str, port: str, protocol: str
    ) -> dict:
        return self.mgmt.slb.virtual_server.vport.delete(
            virtual_server_name=virtual_server, port=port, protocol=protocol, name=None
        )["response"]

    def _extend_responses(self):
        RESPONSE_CODES.update({
            # Address specified is used by a real server
            654311496: {
                '*': {
                    '*': AddressSpecifiedIsInUse
                }
            },
            # Address specified is used already by another virtual server
            654311495: {
                '*': {
                    '*': AddressSpecifiedIsInUse
                }
            },
        })
