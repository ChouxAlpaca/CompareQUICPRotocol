#!/usr/bin/env python3
import os
import json
import re
from datetime import datetime
import statistics

# Directories for result files
HOME = os.path.expanduser("~")
QPERF_DIR = os.path.join(HOME, "build-qperf", "qperf_result")
IPERF_DIR = os.path.join(HOME, "build-qperf", "iperf3_result")

# Time sections in seconds since midnight
TIME_SECTIONS = [
    ("0h-5h59", 0, 5 * 3600 + 59 * 60),
    ("6h-11h59", 6 * 3600, 11 * 3600 + 59 * 60),
    ("12h-17h59", 12 * 3600, 17 * 3600 + 59 * 60),
    ("18h-23h59", 18 * 3600, 23 * 3600 + 59 * 60)
]

def parse_qperf_file(filepath):
    """Parse a qperf result file for throughput and timestamp."""
    throughputs = []
    try:
        filename = os.path.basename(filepath)
        # Extract timestamp from filename, e.g., wlan0_qperf_throughput_rtt_20250605_193815.txt
        timestamp_str = filename.split('_')[-2] + '_' + filename.split('_')[-1].replace('.txt', '')
        start_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
        
        with open(filepath, 'r') as f:
            for line in f:
                match = re.search(r'second (\d+): ([\d.]+) mbit/s', line)
                if match:
                    second = int(match.group(1))
                    throughput = float(match.group(2))  # Already in Mbps
                    throughputs.append((second, throughput))
        return start_time, throughputs
    except Exception as e:
        print(f"Error parsing qperf file {filepath}: {e}")
        return None, []

def parse_iperf_file(filepath):
    """Parse an iperf3 JSON file for throughput and timestamp."""
    throughputs = []
    try:
        filename = os.path.basename(filepath)
        with open(filepath, 'r') as f:
            data = json.load(f)
            # Try to get timestamp from JSON
            try:
                start_time_str = data['start']['timestamp']['time']
                json_time = datetime.strptime(start_time_str, '%a, %d %b %Y %H:%M:%S GMT')
                # Extract timestamp from filename, e.g., wlan0_iperf3_throughput_20250605_035548.json
                filename_time_str = filename.split('_')[-2] + '_' + filename.split('_')[-1].replace('.json', '')
                filename_time = datetime.strptime(filename_time_str, '%Y%m%d_%H%M%S')
                # Use filename timestamp as it reflects actual test start time
                start_time = filename_time
            except (KeyError, ValueError):
                # Fallback to filename if JSON timestamp is missing or invalid
                timestamp_str = filename.split('_')[-2] + '_' + filename.split('_')[-1].replace('.json', '')
                start_time = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            
            for interval in data['intervals']:
                second = interval['sum']['start']
                throughput = interval['sum']['bits_per_second'] / 1e6  # Convert bps to Mbps
                throughputs.append((second, throughput))
        return start_time, throughputs
    except Exception as e:
        print(f"Error parsing iperf3 file {filepath}: {e}")
        return None, []

def get_time_section(seconds_since_midnight):
    """Assign a time value (in seconds) to a time section."""
    for label, start, end in TIME_SECTIONS:
        if start <= seconds_since_midnight <= end:
            return label
    return None

def process_files(directory, parse_func, file_pattern):
    """Process files and group throughputs by interface and time section."""
    data = {
        'wlan0': {'0h-5h59': [], '6h-11h59': [], '12h-17h59': [], '18h-23h59': []},
        'wlan1': {'0h-5h59': [], '6h-11h59': [], '12h-17h59': [], '18h-23h59': []}
    }
    
    for filename in os.listdir(directory):
        if file_pattern in filename:
            filepath = os.path.join(directory, filename)
            start_time, throughputs = parse_func(filepath)
            if start_time is None:
                continue
            interface = 'wlan0' if 'wlan0' in filename else 'wlan1' if 'wlan1' in filename else None
            if not interface:
                continue
            for second, throughput in throughputs:
                seconds_since_midnight = (start_time.hour * 3600 + 
                                        start_time.minute * 60 + 
                                        start_time.second + second)
                section = get_time_section(seconds_since_midnight)
                if section:
                    data[interface][section].append(throughput)
    return data

def calc_stats(values):
    """Calculate mean and standard deviation for a list of values, return as x ± y string."""
    if not values:
        return "0.0 ± 0.0"
    mean = sum(values) / len(values)
    stddev = statistics.stdev(values) if len(values) > 1 else 0.0
    return f"{round(mean, 2)} ± {round(stddev, 2)}"

def print_table(qperf_data, iperf_data):
    """Print a simple table of stats in x ± y format."""
    print("\nWiFi Throughput Statistics (Mbps):")
    print("Time Section   | wlan0 qperf      | wlan1 qperf      | wlan0 iperf3     | wlan1 iperf3     ")
    print("-" * 80)
    for section, _, _ in TIME_SECTIONS:
        w0_q = calc_stats(qperf_data['wlan0'][section])
        w1_q = calc_stats(qperf_data['wlan1'][section])
        w0_i = calc_stats(iperf_data['wlan0'][section])
        w1_i = calc_stats(iperf_data['wlan1'][section])
        print(f"{section:<14} | {w0_q:^16} | {w1_q:^16} | {w0_i:^16} | {w1_i:^16}")

def save_to_csv(qperf_data, iperf_data):
    """Save stats to a CSV file in x ± y format."""
    output_file = os.path.join(HOME, "build-qperf", "wifi_throughput_stats.csv")
    try:
        with open(output_file, 'w') as f:
            f.write("Time Section,wlan0 qperf (Mbps),wlan1 qperf (Mbps),wlan0 iperf3 (Mbps),wlan1 iperf3 (Mbps)\n")
            for section, _, _ in TIME_SECTIONS:
                w0_q = calc_stats(qperf_data['wlan0'][section])
                w1_q = calc_stats(qperf_data['wlan1'][section])
                w0_i = calc_stats(iperf_data['wlan0'][section])
                w1_i = calc_stats(iperf_data['wlan1'][section])
                f.write(f"{section},{w0_q},{w1_q},{w0_i},{w1_i}\n")
        print(f"\nResults saved to {output_file}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def main():
    # Process qperf and iperf3 files
    qperf_data = process_files(QPERF_DIR, parse_qperf_file, 'qperf_throughput_rtt')
    iperf_data = process_files(IPERF_DIR, parse_iperf_file, 'iperf3_throughput')
    
    # Print table
    print_table(qperf_data, iperf_data)
    
    # Save to CSV
    save_to_csv(qperf_data, iperf_data)

if __name__ == "__main__":
    main()
