from api_libs.ip_tools import validate_ip
from api_libs.logger import log
from api_libs.logger import Logger

from conf.static import balancers
from libs.lbr_wrapper import LBR
from libs.model_base import Base
from libs.pool import PoolF5
from libs.virtual_port import VirtualPortA10


logger = Logger()


class VirtualServer(Base):
    def __init__(self, name: str, entrypoint: str, location: str, ip: str, endpoints: dict,
                 port: int = None, http_profile_client: str = None, ssl_profile_client: str = None) -> None:
        super().__init__()
        self.name = name
        self.port = port
        self.http_profile_client = http_profile_client
        self.ssl_profile_client = ssl_profile_client
        self.entrypoint = entrypoint
        self.location = location.upper()
        self.ip = ip
        self.endpoints = endpoints
        self._lbr = None
        self._lbr_wrp = None
        self._virtual_server = dict()

    @property
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.location)
        return self._lbr_wrp


class VirtualServerF5(VirtualServer):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.f5
        return self._lbr

    @log(logger)
    def _get_f5_vs_dict(self, name):
        v = self.lbr.get_virtual_server(name=name)
        if v:
            return v.attrs
        else:
            return {}

    @property
    @log(logger)
    def virtual_server(self):
        if not self._virtual_server:
            item = self._get_f5_vs_dict(name=self.name)
            if item:
                partition, destination = item['destination'].replace('%2', '')[1:].split('/')
                ip, port = item['destination'].replace('%2', '').split('/')[2].split(':')
                # profiles_link = item['profilesReference']['link']
                self._virtual_server = {
                    'name': item['name'],
                    'partition': partition,
                    'destination': ip,
                    'port': port,
                    'pool': item['pool'].split('/')[2],
                    'profiles': {profile['name'] for profile in item['profilesReference']['items']
                                 if profile['name'] not in ['fastL4', 'tcp']}
                }
        return self._virtual_server

    def validate_plan(self):
        if not self.plan['port']:
            logger.log.error('No port in Virtual server plan')
            return False
        if not self.plan['pool']:
            logger.log.error('No pool in Virtual server plan')
            return False
        if not validate_ip(self.plan['destination']):
            logger.log.error(f"Invalid IP in Virtual server plan: {self.plan['destination']}")
            return False
        return True

    def validate_state(self):
        return True

    def create(self) -> bool:
        logger.log.info(f"Create virtual server: {self.plan}")
        return bool(self.lbr.create_virtual_server(name=self.plan['name'], destination=self.plan['destination'],
                                                   port=self.plan['port'], pool=self.plan['pool'],
                                                   http_profile_client=self.http_profile_client,
                                                   ssl_profile_client=self.ssl_profile_client))

    def delete(self) -> bool:
        logger.log.info(f"Delete virtual server: {self.name}")
        return bool(self.lbr.delete_virtual_server(name=self.name))

    @property
    def plan(self):
        if not self._plan:
            partition = balancers[self.location]["F5"]["partition"]
            ports = self.lbr_wrp.get_ports_config(entrypoint=self.entrypoint)
            nodes = [{'name': name} for name in self.endpoints]
            pool_name = self.lbr_wrp.get_pool_name(nodes=nodes, ports=ports, port=self.port)
            self._plan = {
                'name': self.name,
                'partition': partition,
                'destination': self.ip,
                'port': str(self.port),
                'pool': pool_name,
                'profiles': {profile for profile in [self.ssl_profile_client, self.http_profile_client] if profile}
            }
        return self._plan

    @property
    def state(self):
        if not self._state:
            self._state = self.virtual_server
        return self._state

    @property
    def siblings(self):
        if not self._siblings:
            pool_name = self.plan['pool']
            port_config = self.lbr_wrp.get_port_config(entrypoint=self.entrypoint, port=self.port)
            monitor = self.lbr_wrp.get_healthcheck_by_entrypoint(entrypoint=self.entrypoint)
            self._siblings[pool_name] = PoolF5(name=pool_name, location=self.location, endpoints=self.endpoints,
                                               monitor=monitor, port_config=port_config)
        return self._siblings


class VirtualServerA10(VirtualServer):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.a10
        return self._lbr

    @property
    @log(logger)
    def virtual_server(self):
        if not self._virtual_server:
            item = self.lbr.get_virtual_server(name=self.name)
            if item:
                self._virtual_server = {
                    'name': item['name'],
                    'ip': item['ip-address'],
                    'ports': sorted([port['port-number'] for port in item.get('port-list', [])])
                }
        return self._virtual_server

    def validate_plan(self):
        if not self.plan['ports']:
            logger.log.error('No ports in Virtual server plan')
            return False
        if not self.plan['ip']:
            logger.log.error('No IP in Virtual server plan')
            return False
        if not validate_ip(self.plan['ip']):
            logger.log.error(f"Invalid IP in Virtual server plan: {self.plan['ip']}")
            return False
        return True

    def validate_state(self):
        return True

    def global_patch(self):
        return {
            self.__class__.__name__: {
                'patched': self.patch(),
                'siblings': self._get_siblings_data('patch')
            }
        }

    def global_delete(self):
        siblings_data = self._get_siblings_data('delete')
        self_deleted = self.delete()

        return {
            self.__class__.__name__: {
                'deleted': self_deleted,
                'siblings': siblings_data
            }
        }

    def create(self) -> bool:
        logger.log.info(f"Create virtual server: {{'name': {self.plan['name']}, 'ip': {self.plan['ip']}}}")
        return bool(self.lbr.create_virtual_server(name=self.plan['name'], ip=self.plan['ip']))

    def delete(self) -> bool:
        logger.log.info(f"Delete virtual server: {self.name}")
        response = self.lbr.delete_virtual_server(name=self.name)
        return True if response['status'] == "OK" else False

    @property
    def plan(self):
        if not self._plan:
            ports = self.lbr_wrp.get_ports_config(entrypoint=self.entrypoint)
            self._plan = {
                'name': self.name,
                'ip': self.ip,
                'ports': sorted([item['port'] for item in ports])
            }
        return self._plan

    @property
    def state(self):
        if not self._state:
            self._state = self.virtual_server
        return self._state

    @property
    def siblings(self):
        if not self._siblings:
            ports = self.lbr_wrp.get_ports_config(entrypoint=self.entrypoint)
            sg_healthcheck = self.lbr_wrp.get_healthcheck_by_entrypoint(entrypoint=self.entrypoint)
            for item in ports:
                self._siblings[f"{item['port']}_{item['protocol']}"] = VirtualPortA10(
                    virtual_server_name=self.plan['name'], port_config=item,
                    location=self.location, endpoints=self.endpoints, sg_health=sg_healthcheck,
                    client_ssl=self.ssl_profile_client
                )
        return self._siblings
