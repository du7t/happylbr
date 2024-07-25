# Migrate from RT to Netbox

## Implement:

* rt.getServerLocation - not needed
* rt.removeSharedIP - what is shared IP?
* rt.reserveIPForNodes -> inventory.reserve_ip_for_nodes
* rt.findInterfaces -> inventory.get_interfaces
* rt.getServerEnvironment - not needed
* rt.get_nic0 -> inventory.get_nic0
