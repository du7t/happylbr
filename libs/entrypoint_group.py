import api_libs.ads_mini as ads
import api_libs.ip_tools as ip_tools
from api_libs.helper import get_ff
from api_libs.inventory import Inventory
from api_libs.logger import Logger

from libs.entrypoint import Entrypoint
from libs.model_base import Base


logger = Logger()


class EntrypointGroup(Base):
    def __init__(self, service_name: str, env_name: str, env: ads.Env, entrypoints: list) -> None:
        super().__init__()
        self.name = service_name.lower()
        self.env_name = env_name
        self.env = env
        self.entrypoints = entrypoints
        self._endpoints = dict()
        self.inv = Inventory(mode=get_ff('INVENTORY_MODE'), netbox_api=get_ff('NETBOX_API'),
                             netbox_token=get_ff('NETBOX_TOKEN'), rt_api=get_ff('RT')['DOMAIN'])

    @property
    def endpoints(self):
        if not self._endpoints:
            host_ips = self.get_endpoints_from_ads()
            for item in host_ips:
                interfaces = self.inv.get_interfaces(hostname=item['name'])
                self._endpoints[item['name']] = {
                    'ip': item['ip'],
                    'interfaces': sorted([(interface['name'], interface['ip']) for interface in interfaces])
                }
        return self._endpoints

    @staticmethod
    def get_resolvable_servers(servers: list) -> list[dict]:
        resolvable_servers = []

        for server in servers:
            result = ip_tools.nslookup(server)
            if result.get('A'):
                resolvable_servers.append({"name": server.split(".", 1)[0], "ip": result['A'][0]})

        return resolvable_servers

    def get_endpoints_from_ads(self) -> list:
        resolvable_servers = []
        servers = self.env.get_hosts_by_service(self.name)
        if servers:
            resolvable_servers = EntrypointGroup.get_resolvable_servers(servers)
        return resolvable_servers

    @property
    def siblings(self):
        if not self._siblings and self.are_we_good():
            for entrypoint in self.entrypoints:
                self._siblings[entrypoint] = Entrypoint(name=entrypoint, env=self.env, endpoints=self.endpoints,
                                                        inventory=self.inv)
        return self._siblings

    @property
    def state(self):
        if not self._state:
            interfaces = list()
            for hostname in self.endpoints.keys():
                for item in self.endpoints[hostname]['interfaces']:
                    if item[0] != 'nic0':
                        interfaces.append(f'{hostname}:{item[0]}')

            self._state = {
                'name': self.name,
                'interfaces': sorted(interfaces)
            }
        return self._state

    @property
    def plan(self):
        if not self._plan:
            interfaces = list()
            for hostname in self.endpoints.keys():
                for entrypoint in self.entrypoints:
                    interfaces.append(f'{hostname}:{entrypoint}')
            self._plan = {
                'name': self.name,
                'interfaces': sorted(interfaces)
            }
        return self._plan

    def validate_state(self):
        # We consider having unknown interface unaccepatable
        planned_interfaces = self.plan['interfaces']
        current_interfaces = self.state['interfaces']
        for interface in current_interfaces:
            if interface not in planned_interfaces:
                logger.log.error(f'Unknown interface {interface}')
                return False
        return True

    def validate_plan(self):
        if not self.plan['interfaces']:
            logger.log.error(f'No endpoints found for service: {self.name}')
            return False
        return True
