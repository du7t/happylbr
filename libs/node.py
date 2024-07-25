from api_libs.logger import log
from api_libs.logger import Logger

from libs.f5_wrapper import Exists
from libs.lbr_wrapper import LBR
from libs.model_base import Base


logger = Logger()


class Node(Base):
    def __init__(self, name: str, ip: str, location: str) -> None:
        super().__init__()
        self.name = name
        self.ip = ip
        self.location = location.upper()
        self._lbr = None
        self._lbr_wrp = None
        self._node = dict()

    @property
    def lbr_wrp(self):
        if not self._lbr_wrp:
            self._lbr_wrp = LBR(location=self.location)
        return self._lbr_wrp


class NodeF5(Node):

    @property
    def lbr(self):
        if not self._lbr:
            self._lbr = self.lbr_wrp.f5
        return self._lbr

    @property
    @log(logger)
    def node(self):
        if not self._node:
            item = self.lbr.get_node(name=self.name)
            if item:
                self._node = {
                    'name': item.attrs['name'],
                    'ip': item.attrs['address'].split('%')[0]
                }
        return self._node

    def validate_plan(self):
        if not self.plan['ip']:
            logger.log.error('No IP in Node plan')
            return False
        return True

    def validate_state(self):
        return True

    def create(self) -> bool:
        logger.log.info(f"Create node: {self.plan}")
        try:
            return bool(self.lbr.create_node(name=self.plan['name'], address=self.plan['ip']))
        except Exists:
            return False

    @log(logger)
    def patch(self) -> bool:
        if not self.are_we_good():
            return False

        if self.diff:
            if self.state and 'ip' in self.diff:
                logger.log.info(f"Found diff in node {self.name} ip: {self.diff}")
                processed_pools = {}
                node_references = self.lbr.get_node_references(name=self.state['name'])
                logger.log.info(f"Got node references: {node_references}")
                for pool in node_references:
                    logger.log.info(f"Delete members by node in pool: {pool}")
                    processed_pools[pool] = self.lbr.delete_pool_members_by_nodes(name=pool, nodes=[self.state['name']])
                self.delete()
                self.create()
                for pool, members in processed_pools.items():
                    logger.log.info(f"Add pool '{pool}' members: {members}")
                    self.lbr.add_pool_members(name=pool, members=members)
            elif not self.state:
                self.create()
        else:
            logger.log.info(f"{self.__class__.__name__} - no diff, state: {self.state}")

        return True

    def delete(self) -> bool:
        logger.log.info(f"Delete node: {self.name}")
        node_references = self.lbr.get_node_references(name=self.name)
        if not node_references:
            return self.lbr.delete_node(name=self.name)
        else:
            logger.log.warn(f'Cannot delete node {self.name}: used in {node_references}')
            return False

    @property
    def plan(self):
        if not self._plan:
            self._plan = {
                'name': self.name,
                'ip': self.ip
            }
        return self._plan

    @property
    def state(self):
        if not self._state:
            self._state = self.node
        return self._state
