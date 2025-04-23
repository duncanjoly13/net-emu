### Dependencies
* mininet

### Usage
1. Start the mininet topology:
```bash
$ python3 topo.py
```
2. Start the controller:
```bash
$ sudo python3 bandwidth_control.py <interface> <trace file> <latency>
```
3. Test latency in the mininet console:
```bash
mininet> h1 ping h2 -c 5
```
4. Test bandwidth in the mininet console:
```bash
mininet> h2 iperf -s &
mininet> h1 iperf -c h2 -t 10
```

The latency and throughput should match the values in the trace file and the provided latency argument, respectively.