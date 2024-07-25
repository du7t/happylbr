"""f5-sdk wrapper"""
from f5.bigip import ManagementRoot
from f5.bigip.tm.ltm.node import Node
from f5.bigip.tm.ltm.pool import Members
from f5.bigip.tm.ltm.pool import Pool
from f5.bigip.tm.ltm.virtual import Virtual
from icontrol.exceptions import iControlUnexpectedHTTPError


class F5Manager:
    def __init__(self, address: str, user: str, password: str, partition: str) -> None:
        self._mgmt = None
        self.address = address
        self.user = user
        self.password = password
        self.partition = partition
        self._nodes = None
        self._pools = None
        self._virtuals = None

    @property
    def mgmt(self):
        if not self._mgmt:
            self._mgmt = ManagementRoot(self.address, self.user, self.password)
        return self._mgmt

    @staticmethod
    def clean_value(value: str) -> str:
        if value:
            return value.rsplit("/", 1)[-1].rsplit("%", 1)[0].rsplit(":", 1)[0]

    @property
    def nodes(self) -> list[Node]:
        if not self._nodes:
            self._nodes = self.mgmt.tm.ltm.nodes.get_collection()
        return self._nodes

    @property
    def pools(self) -> list[Pool]:
        if not self._pools:
            requests_params = {
                "suffix": "/?&expandSubcollections=true",
                "uri_as_parts": True,
            }
            self._pools = self.mgmt.tm.ltm.pools.get_collection(
                requests_params=requests_params
            )
        return self._pools

    @property
    def virtuals(self) -> list[Virtual]:
        if not self._virtuals:
            self._virtuals = self.mgmt.tm.ltm.virtuals.get_collection()
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
        if data_type == "node":
            self._nodes = None
        elif data_type == "pool":
            self._pools = None
        elif data_type == "virtual":
            self._virtuals = None

    # Nodes
    def node_exists(self, name: str) -> bool:
        return self.mgmt.tm.ltm.nodes.node.exists(name=name, partition=self.partition)

    @refresh_on_change(data_type="node")
    def create_node(self, name: str, address: str, monitor: str = "icmp") -> Node:
        try:
            return self.mgmt.tm.ltm.nodes.node.create(
                name=name, address=address, partition=self.partition, monitor=monitor
            )
        except iControlUnexpectedHTTPError as e:
            if e.response.status_code == 409 and "01020066:3" in e.response.json().get("message"):
                raise Exists(e)
            elif e.response.status_code == 400 and "0107176c:3" in e.response.json().get("message"):
                raise AddressSpecifiedIsInUse(e)
            else:
                raise

    def get_node(self, name: str) -> Node:
        if self.node_exists(name=name):
            return self.mgmt.tm.ltm.nodes.node.load(name=name, partition=self.partition)

    # Using collection
    # def get_node(self, name: str) -> Node:
    #     for node in self.nodes:
    #         if node.name == name:
    #             return node

    def get_node_by_address(self, address: str) -> Node:
        for node in self.nodes:
            if self.clean_value(node.address) == address:
                return node

    def get_node_address(self, name: str) -> str:
        if node := self.get_node(name=name):
            return self.clean_value(node.address)

    def get_node_references(self, name: str) -> set[str]:
        used_in_pools = set()
        for pool in self.pools:
            for member in pool.membersReference.get("items", []):
                if self.clean_value(member["name"]) == name:
                    used_in_pools.add(pool.name)
        return used_in_pools

    @refresh_on_change(data_type="node")
    def delete_node(self, name: str) -> bool:
        if node := self.get_node(name=name):
            node.delete()
            return True
        return False

    @refresh_on_change(data_type="node")
    def delete_node_by_address(self, address: str) -> bool:
        if node := self.get_node_by_address(address=address):
            node.delete()
            return True
        return False

    # Pools and Members
    def pool_exists(self, name: str) -> bool:
        return self.mgmt.tm.ltm.pools.pool.exists(name=name, partition=self.partition)

    @refresh_on_change(data_type="pool")
    def create_pool(
        self, name: str, members: list[str] = None, monitor: str = "tcp"
    ) -> Pool:
        try:
            return self.mgmt.tm.ltm.pools.pool.create(
                name=name, members=members, partition=self.partition, monitor=monitor
            )
        except iControlUnexpectedHTTPError as e:
            if e.response.status_code == 409 and "01020066:3" in e.response.json().get("message"):
                raise Exists(e)
            else:
                raise

    # Using collection
    # def get_pool(self, name: str) -> Pool:
    #     for pool in self.pools:
    #         if pool.name == name:
    #             return pool

    def get_pool(self, name: str) -> Pool:
        if self.pool_exists(name=name):
            return self.mgmt.tm.ltm.pools.pool.load(
                name=name,
                partition=self.partition,
                suffix="/?&expandSubcollections=true",
            )

    def get_pool_references(self, name: str) -> set[str]:
        used_in_virtuals = set()
        for virtual in self.virtuals:
            if self.clean_value(virtual.attrs.get("pool")) == name:
                used_in_virtuals.add(virtual.name)
        return used_in_virtuals

    @refresh_on_change(data_type="pool")
    def delete_pool(self, name: str) -> bool:
        if pool := self.get_pool(name=name):
            pool.delete()
            return True
        return False

    def get_pool_members(self, name: str) -> list[dict]:
        if pool := self.get_pool(name=name):
            return [
                {
                    "name": member["name"].split(":")[0],
                    "address": self.clean_value(member["address"]),
                    "port": int(member["name"].rsplit(":")[-1]),
                }
                for member in pool.membersReference.get("items", [])
            ]
        else:
            return []

    def get_pool_monitor(self, name: str) -> str:
        if pool := self.get_pool(name=name):
            monitor = pool.attrs.get('monitor')
            if monitor:
                return monitor.split('/')[2]
            else:
                return ''
        else:
            return ''

    def get_pool_members_names(self, name: str) -> list[str]:
        return list({member["name"] for member in self.get_pool_members(name=name)})

    def pool_member_exists(self, pool_name: str, member_name: str) -> bool:
        if pool := self.get_pool(name=pool_name):
            return pool.members_s.members.exists(
                name=member_name, partition=self.partition
            )

    def get_pool_member(self, pool_name: str, member_name: str) -> Members:
        if pool := self.get_pool(name=pool_name):
            return pool.members_s.members.load(
                name=member_name, partition=self.partition
            )

    def collect_pool_members(self, name: str) -> list[Members]:
        if pool := self.get_pool(name=name):
            return pool.members_s.get_collection()

    @refresh_on_change(data_type="pool")
    def add_pool_members(self, name: str, members: list[str]) -> list[str]:
        added_members = []
        if pool := self.get_pool(name=name):
            for member in members:
                pool.members_s.members.create(name=member, partition=self.partition)
                added_members.append(member)
        return added_members

    @refresh_on_change(data_type="pool")
    def delete_pool_members_by_nodes(self, name: str, nodes: list[str]) -> list[str]:
        deleted_members = []
        current_members = self.collect_pool_members(name=name)
        for member in current_members:
            if member.name.split(':')[0] in nodes:
                deleted_members.append(member.name)
                member.delete()
        return deleted_members

    @refresh_on_change(data_type="pool")
    def delete_all_pool_members(self, name: str) -> list[str]:
        deleted_members = []
        members = self.collect_pool_members(name=name)
        for member in members:
            deleted_members.append(member.name)
            member.delete()
        return deleted_members

    # Virtual Servers and profiles
    def virtual_server_exists(self, name: str) -> bool:
        return self.mgmt.tm.ltm.virtuals.virtual.exists(
            name=name, partition=self.partition
        )

    @refresh_on_change(data_type="virtual")
    def create_virtual_server(
        self,
        name: str,
        destination: str,
        port: str,
        pool: str = None,
        http_profile_client: str = None,
        ssl_profile_client: str = None,
    ) -> Virtual:
        try:
            profiles = [
                {"name": profile}
                for profile in [http_profile_client, ssl_profile_client]
                if profile
            ]
            virtual_server_config = {
                "name": name,
                "destination": f"{destination}:{port}",
                "pool": pool,
                "profiles": profiles,
                "snat": "automap",
                "partition": self.partition,
            }
            return self.mgmt.tm.ltm.virtuals.virtual.create(**virtual_server_config)
        except iControlUnexpectedHTTPError as e:
            if e.response.status_code == 409 and "01020066:3" in e.response.json().get("message"):
                raise Exists(e)
            elif e.response.status_code == 400 and "illegally shares destination address" in e.response.json().get("message"):
                raise AddressSpecifiedIsInUse(e)
            else:
                raise

    def get_virtual_server(self, name: str) -> Virtual:
        if self.virtual_server_exists(name=name):
            return self.mgmt.tm.ltm.virtuals.virtual.load(
                name=name, partition=self.partition, suffix="/?&expandSubcollections=true"
            )

    def get_virtual_servers_by_ip(self, ip: str) -> list[Virtual]:
        virtuals = []
        for virtual in self.virtuals:
            if self.clean_value(virtual.attrs.get("destination")) == ip:
                virtuals.append(virtual)
        return virtuals

    def get_virtual_server_ip(self, name: str) -> str:
        virtual = self.get_virtual_server(name=name)
        if virtual:
            return self.clean_value(virtual.attrs.get("destination"))

    def get_virtual_server_pool(self, name: str) -> str:
        virtual = self.get_virtual_server(name=name)
        if virtual:
            return self.clean_value(virtual.attrs.get("pool"))

    # Using collection
    # def get_virtual_server(self, name: str) -> Virtual:
    #     for virtual in self.virtuals:
    #         if virtual.name == name:
    #             return virtual

    @refresh_on_change(data_type="virtual")
    def delete_virtual_server(self, name: str) -> bool:
        if virtual := self.get_virtual_server(name=name):
            virtual.delete()
            return True
        return False

    def virtual_profile_exists(
        self, virtual_name: str, profile_name: str, partition: str = "Common"
    ) -> bool:
        if virtual := self.get_virtual_server(name=virtual_name):
            return virtual.profiles_s.profiles.exists(
                name=profile_name, partition=partition
            )


class Exists(iControlUnexpectedHTTPError):
    pass


class AddressSpecifiedIsInUse(iControlUnexpectedHTTPError):
    pass
