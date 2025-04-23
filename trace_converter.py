"""
trace_converter.py: trace file converter script

Converts a CSV file with time and throughput data into the format taken by bandwidth_control.py.
"""

import sys


def convert(input_file: str, output_file: str) -> None:
    """
    Converts a CSV file with time and throughput data into the format taken by bandwidth_control.py.

    :param input_file: input CSV file containing throughput data with time offset of one second per line
    :param output_file: output CSV file to write the converted data
    """
    with open(input_file) as infile, open(output_file, 'w') as outfile:
        # Write header to output file
        outfile.write("# Time (s), Throughput (kbps)\n")

        # Since the input file is expected to have one throughput value per line and each line represents one second,
        # we can use a simple counter as the time offset.
        counter = 0

        for line in infile:
            # Skip empty lines and comments
            if not line.strip() or line.startswith('#') or line.startswith('UL'):
                continue

            throughput = int(float(line.strip()) * 1000)  # Convert to kbps
            outfile.write(f"{counter},{throughput}\n")
            counter += 1

        infile.close()
        outfile.close()

    print(f"Converted {input_file} to {output_file} successfully. The output file is ready for use with "
          f"bandwidth_control.py and has data for {counter} seconds ({(counter/60):.3f} minutes).")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 trace_converter.py <input file> <output file>")
        print("Example: python3 bandwidth_control.py trace.csv trace_converted.csv")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    try:
        convert(input_file, output_file)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
