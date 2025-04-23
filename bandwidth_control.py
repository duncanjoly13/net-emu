"""
bandwidth_control.py: Dynamically adjusts bandwidth and sets latency using tc

Reads a trace file (CSV: time_offset_sec, throughput_kbps) and applies bandwidth limits to a specified interface using
tc htb. Also adds a fixed latency using tc netem.

Requires root privileges to run tc commands.
"""

import subprocess
import time
import sys
import csv
import signal

# Setup
DEFAULT_LATENCY_MS = "50ms"  # Default fixed latency to add
DEFAULT_BURST_BYTES = 15000  # HTB burst buffer size (bytes)
target_interface = None


def run_tc_command(command: str) -> None:
    """Executes a tc command using subprocess and handles errors."""
    full_command = f"sudo tc {command}"
    print(f"Executing: {full_command}")
    try:
        # Use check=False initially to see if commands run without erroring out immediately
        result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            # Print errors but don't raise immediately unless it's critical
            print(f"Warning/Error executing tc command: {command}")
            print(f"Return Code: {result.returncode}")
            print(f"Stderr: {result.stderr}")
            print(f"Stdout: {result.stdout}")
            # Allow deletion errors to pass more easily
            if "delete" in command and (
                    "RTNETLINK answers: No such file or directory" in result.stderr or
                    "Cannot find device" in result.stderr):
                pass  # Ignore errors deleting non-existent things
    except Exception as e:
        print(f"Critical error running subprocess: {e}")
        raise


def cleanup_tc(signum: int = None, frame: int = None) -> None:
    """
    Removes the tc qdisc configuration on exit. Parameters are to make it compatible with signal handling yet are
    not used.

    :param signum: Signal number (optional).
    :param frame: Current stack frame (optional).
    """
    global target_interface
    if target_interface:
        print(f"\nCleaning up tc configuration on {target_interface}...")
        # Ignore errors if already cleaned up or never set
        try:
            run_tc_command(f"qdisc del dev {target_interface} root")
            print("Cleanup successful.")
        except Exception as e:
            print(f"Cleanup partially failed or qdisc already removed: {e}")
    sys.exit(0)


def apply_bandwidth_latency(interface: str, rate_kbps: int, latency_ms: str) -> None:
    """
    Applies or changes the HTB rate AND adds netem latency.

    :param interface: Network interface to apply the settings to.
    :param rate_kbps: Bandwidth limit in kbps.
    :param latency_ms: Latency to apply (e.g., "50ms").
    """
    global target_interface
    target_interface = interface

    rate_kbit = int(rate_kbps)
    burst_bytes = DEFAULT_BURST_BYTES

    # Try deleting existing root qdisc first for a clean slate
    run_tc_command(f"qdisc del dev {interface} root")
    time.sleep(0.1)  # Short pause after deletion

    # Add root HTB qdisc
    run_tc_command(f"qdisc add dev {interface} root handle 1: htb default 10")

    # Add base HTB class with initial rate
    run_tc_command(f"class add dev {interface} parent 1: classid 1:1 htb rate {rate_kbit}kbit burst {burst_bytes}")

    # Add netem qdisc for latency under the HTB class 1:1
    run_tc_command(f"qdisc add dev {interface} parent 1:1 handle 10: netem delay {latency_ms}")

    # Add filter to classify all IP traffic into the rate-limited class 1:1
    run_tc_command(
        f"filter add dev {interface} parent 1: protocol ip prio 1 u32 match ip src 0.0.0.0/0 match ip dst "
        f"0.0.0.0/0 flowid 1:1")

    print(f"Initial setup complete for {interface}: Rate={rate_kbit}kbit, Latency={latency_ms}")


def change_bandwidth(interface: str, rate_kbps: int) -> None:
    """
    Changes the rate of the existing HTB class. Latency remains.

    :param interface: Network interface to apply the settings to.
    :param rate_kbps: New bandwidth limit in kbps.
    """
    rate_kbit = int(rate_kbps)
    burst_bytes = DEFAULT_BURST_BYTES
    # Only change the class rate, the netem qdisc attached to it remains.
    run_tc_command(f"class change dev {interface} parent 1: classid 1:1 htb rate {rate_kbit}kbit burst {burst_bytes}")
    print(f"Changed bandwidth on {interface} to {rate_kbit}kbit")


if __name__ == "__main__":
    # Re-add optional latency argument
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: sudo python3 bandwidth_control.py <interface> <trace_file.csv> [latency_ms]")
        print("Example: sudo python3 bandwidth_control.py s1-eth2 throughput_trace.csv 50")
        sys.exit(1)

    interface = sys.argv[1]
    trace_file = sys.argv[2]
    # Parse latency argument or use default
    latency = sys.argv[3] + "ms" if len(sys.argv) == 4 else DEFAULT_LATENCY_MS

    # Register signal handler for cleanup on Ctrl+C
    signal.signal(signal.SIGINT, cleanup_tc)
    signal.signal(signal.SIGTERM, cleanup_tc)

    print(f"Starting bandwidth control on interface {interface}")
    print(f"Using trace file: {trace_file}")
    print(f"Applying fixed latency: {latency}")  # Re-enabled latency message

    start_time = time.time()
    last_offset = 0
    initial_rate_set = False

    try:
        with open(trace_file) as f:
            reader = csv.reader(f)
            rows_to_process = []
            # Read all rows first to handle potential header properly
            all_rows = list(reader)
            if all_rows and (all_rows[0][0].strip().startswith('#') or all_rows[0][0].strip().lower() == 'time (s)'):
                rows_to_process = all_rows[1:]  # Skip header
            else:
                rows_to_process = all_rows  # No header or first row is data

            if not rows_to_process:
                print("Error: Trace file is empty or contains only a header.")
                sys.exit(1)

            for row in rows_to_process:
                if not row or (len(row) > 0 and row[0].strip().startswith('#')):
                    continue  # Skip empty lines and comments in body

                try:
                    time_offset = float(row[0])
                    throughput_kbps = int(row[1])
                except (ValueError, IndexError):
                    print(f"Skipping invalid row: {row}")
                    continue

                # Calculate time to sleep until the next change
                current_time = time.time()
                target_exec_time = start_time + time_offset
                sleep_duration = target_exec_time - current_time

                if sleep_duration > 0:
                    print(f"Sleeping for {sleep_duration:.2f} seconds...")
                    time.sleep(sleep_duration)

                if throughput_kbps < 0:
                    print("End of trace signal received.")
                    break  # Exit loop if throughput is negative

                if not initial_rate_set:
                    # Apply initial bandwidth AND latency
                    apply_bandwidth_latency(interface, throughput_kbps, latency)
                    initial_rate_set = True
                else:
                    # Change bandwidth for subsequent entries (latency stays)
                    change_bandwidth(interface, throughput_kbps)

                last_offset = time_offset

    except FileNotFoundError:
        print(f"Error: Trace file not found at {trace_file}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        # Ensure cleanup happens even if the script ends normally or via error
        cleanup_tc()
