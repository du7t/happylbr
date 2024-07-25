from api_libs.logger import log
from api_libs.logger import Logger

from libs.lbr_wrapper import LBR
from libs.model_base import Base
from libs.node import NodeF5
from libs.f5_wrapper import Exists

logger = Logger()


class Pool(Base):
    def __init__(self, name: str, location: str, endpoints: dict, monitor: str, port_config: dict) -> None:
        super().__init__()
        self.name = name
        self.location = location.upper()
        self.endpoints = endpoints
        self.monitor = monitor
        self.port_config = port_config
        self._lbr = None
        self._lbr_wrp = None
        self._pool = dict()

    @property
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.location)
        return self._lbr_wrp


class PoolF5(Pool):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.f5
        return self._lbr

    @property
    @log(logger)
    def pool(self):
        if not self._pool:
            item = self.lbr.get_pool(name=self.name)
            if item:
                self._pool = {
                    'name': item.attrs['name'],
                    'monitor': item.attrs.get('monitor', '').split('/')[-1],
                    'members': [member['name'] for member in item.attrs.get('membersReference', {}).get('items', [])]
                }
        return self._pool

    def validate_plan(self):
        if not self.plan['name']:
            logger.log.error('No name in Pool plan')
            return False
        return True

    def validate_state(self):
        return True

    def get_members(self):
        members = []
        for endpoint, interfaces in self.endpoints.items():
            members.append(f'{endpoint}:{self.port_config["target_port"]}')
        return members

    @property
    def plan(self):
        if not self._plan:
            self._plan = {
                'name': self.name,
                'monitor': self.monitor,
                'members': self.get_members()
            }
        return self._plan

    def create(self) -> bool:
        logger.log.info(f"Create pool: {self.plan}")
        try:
            return bool(self.lbr.create_pool(name=self.plan['name'], members=self.plan['members'],
                                             monitor=self.plan['monitor']))
        except Exists:
            return False

    @log(logger)
    def patch(self) -> bool:
        if not self.are_we_good():
            return False

        if self.diff:
            if self.state and 'members' in self.diff:
                logger.log.info(f"Found diff in pool {self.name} members: {self.diff}")
                logger.log.info("Delete current pool members")
                self.lbr.delete_all_pool_members(name=self.state['name'])
                logger.log.info(f"Add new pool members: {self.plan['members']}")
                self.lbr.add_pool_members(name=self.plan['name'], members=self.plan['members'])
            elif not self.state:
                self.create()
        else:
            logger.log.info(f"{self.__class__.__name__} - no diff, state: {self.state}")

        return True

    def delete(self) -> bool:
        logger.log.info(f"Delete pool: {self.name}")
        pool_references = self.lbr.get_pool_references(name=self.name)
        if not pool_references:
            return self.lbr.delete_pool(name=self.name)
        else:
            logger.log.warn(f'Cannot delete pool {self.name}: used in {pool_references}')
            return False

    @property
    def state(self):
        if not self._state:
            self._state = self.pool
        return self._state

    @property
    def siblings(self):
        if not self._siblings and self.validate_plan():
            for endpoint, value in self.endpoints.items():
                self._siblings[endpoint] = NodeF5(
                    name=endpoint, ip=value['ip'],
                    location=self.location
                )
        return self._siblings
