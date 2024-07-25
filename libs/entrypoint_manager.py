import api_libs.ads_mini as ads
from api_libs.helper import get_ff
from api_libs.logger import Logger

from conf import static
from libs.entrypoint import Entrypoint
from libs.entrypoint_group import EntrypointGroup

logger = Logger()


class EntrypointManager:
    def __init__(self, env_name: str) -> None:
        self.env_name = env_name
        self._env = None
        self.entrypoint = None
        self.eg_store = dict()

    @property
    def env(self):
        if not self._env:
            self._env = ads.Env(env_name=self.env_name, user=get_ff('ADS')["user"], pwd=get_ff('ADS')["password"],
                                cache_ttl=get_ff('CACHE_TTL'))
            if not self._env.find_env(name=self.env_name):
                raise ValueError(f'Incorrect env name given {self.env_name}')
            self._env.prepare(clear_cache_on_start=get_ff('CLEAR_CACHE_ON_START'))
        return self._env

    def get_eg(self, service: str) -> EntrypointGroup:
        """ To avoid recreating EG for every entrypoint we store it in self.eg_store """
        if service not in self.eg_store:
            service_entrypoints = sorted(EntrypointManager.get_entrypoints(services=[service]))
            self.eg_store[service] = EntrypointGroup(service_name=service, env_name=self.env_name, env=self.env,
                                                     entrypoints=service_entrypoints)
        return self.eg_store[service]

    def global_plan(self, service: str):
        eg = self.get_eg(service)
        return eg.global_plan

    def global_state(self, service: str):
        eg = self.get_eg(service)
        return eg.global_state

    def global_diff(self, service: str):
        eg = self.get_eg(service)
        return eg.global_diff

    def create_entrypoint(self, entrypoint: str) -> dict:
        self.entrypoint = entrypoint

        # We need service and EG to calculate endpoints and to run EG level state validation
        service = EntrypointManager.get_service_by_entrypoint(entrypoint)
        eg = self.get_eg(service)
        if get_ff('CHECK_ENTRYPOINT_GROUP') and not eg.are_we_good():
            raise Exception(f"'{entrypoint}' - entrypoint group '{service}' is not valid, see logs")
        if not eg.endpoints:
            raise Exception(f'No hosts for {eg.name} service found')
        ep = Entrypoint(name=entrypoint, env=eg.env, endpoints=eg.endpoints)
        logger.log.info(f"'{entrypoint}' - create entrypoint with endpoints: {list(eg.endpoints.keys())}")
        return ep.global_patch()

    def delete_entrypoint(self, entrypoint: str) -> dict:
        self.entrypoint = entrypoint

        service = EntrypointManager.get_service_by_entrypoint(entrypoint)
        eg = self.get_eg(service)
        if get_ff('CHECK_ENTRYPOINT_GROUP') and not eg.validate_state():
            raise Exception(f"'{entrypoint}' - entrypoint group '{service}' state is not valid, see logs")

        ep = Entrypoint(name=entrypoint, env=eg.env, endpoints=eg.endpoints)
        logger.log.info(f"'{entrypoint}' - delete entrypoint with endpoints: {list(eg.endpoints.keys())}")
        return ep.global_delete()

    @staticmethod
    def get_entrypoints(entrypoints=None, services=None, mandatory: bool = False) -> list:
        """
        Build list of VIPs from entrypoints and services
        Args:
            entrypoints: List of entrypoints
            services: List of services
        Returns:
            list of VIPs
        """
        data = []

        if entrypoints:
            data = [vip for vip in entrypoints if vip in static.entrypoints.keys()]
        elif services:
            data = [vip for vip, data in static.entrypoints.items() if data["service"] in services]
        elif mandatory:
            data = [vip for vip, data in static.entrypoints.items() if data["mandatory"]]

        return data

    @staticmethod
    def get_service_by_entrypoint(entrypoint: str) -> str:
        data = static.entrypoints.get(entrypoint, None)
        if data and 'service' in data:
            return data['service']
        else:
            return None

    @staticmethod
    def have_balancers(location: str) -> bool:
        return location in static.balancers
