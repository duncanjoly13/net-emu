"""
topology.py: Simple Mininet topology script

Creates a network with two hosts (h1, h2) connected via a switch (s1).
No explicit controller is used; explicitly sets OVS switch to operate in standalone learning switch mode.
Does not initially set link parameters, as the control script will handle them.
"""

from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def create_topology() -> None:
    """Creates and runs the simple topology."""

    # Create a Mininet object
    net = Mininet(autoSetMacs=True)

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24')
    h2 = net.addHost('h2', ip='10.0.0.2/24')

    info('*** Adding switch\n')
    # The switch added here will operate as a learning switch
    s1 = net.addSwitch('s1', failMode='standalone')

    info('*** Creating links\n')
    # Connect hosts to switch using default Link type.
    net.addLink(h1, s1)
    net.addLink(h2, s1)

    info('*** Starting network\n')
    net.build()
    info('*** Starting switch\n')
    s1.start([])

    # The OVS switch s1 should now operate as a learning switch

    info('*** Network started.\n\n')
    info('*** Run the bandwidth control script in a separate terminal.\n')
    info('*** Example: sudo python3 bandwidth_control.py s1-eth2 trace.csv 50\n')  # Assuming h2 is on s1-eth2

    # Start the Mininet Command Line Interface
    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    create_topology()
