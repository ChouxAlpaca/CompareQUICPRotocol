#!/usr/bin/env bash
# wifi24h_test.sh: 24-hour Wi-Fi throughput and RTT test on wlan0 and wlan1

# Server and port configuration
SERVER="222.252.4.92"
QPERF_PORT="18080"
IPERF_PORT="18081"
IFACE1_NAME="wlan0"
IFACE1_IP="192.168.1.15"
IFACE2_NAME="wlan1"
IFACE2_IP="192.168.61.47"

# Log directories inside build-qperf
QPERF_LOGDIR="$HOME/build-qperf/qperf_result"
IPERF_LOGDIR="$HOME/build-qperf/iperf3_result"
mkdir -p "$QPERF_LOGDIR"  # Create the qperf_result directory if it doesn't exist
mkdir -p "$IPERF_LOGDIR"  # Create the iperf3_result directory if it doesn't exist

# Function to disable a network interface
disable_interface() {
    sudo ifconfig "$1" down
    echo "[$(date)] $1 disabled."
}

# Function to enable a network interface
enable_interface() {
    sudo ifconfig "$1" up
    echo "[$(date)] $1 enabled."
}

# Function to measure throughput and RTT using qperf
measure_throughput_qperf() {
    local iface=$1
    echo "[$(date)] Running qperf on $iface..."
    cd "$HOME/build-qperf"
    ./qperf -c "$SERVER" -p "$QPERF_PORT" -t 60 > "$QPERF_LOGDIR/${iface}_qperf_throughput_rtt_$(date +%Y%m%d_%H%M%S).txt"
    echo "[$(date)] qperf test completed on $iface. Results saved to $QPERF_LOGDIR/${iface}_qperf_throughput_rtt_$(date +%Y%m%d_%H%M%S).txt"
}

# Function to measure throughput using iperf3
measure_throughput_iperf3() {
    local iface=$1
    local ip=$2
    echo "[$(date)] Running iperf3 on $iface..."
    iperf3 -c "$SERVER" -p "$IPERF_PORT" -R -t 60 -B "$ip" -J > "$IPERF_LOGDIR/${iface}_iperf3_throughput_$(date +%Y%m%d_%H%M%S).json"
    echo "[$(date)] iperf3 test completed on $iface. Results saved to $IPERF_LOGDIR/${iface}_iperf3_throughput_$(date +%Y%m%d_%H%M%S).json"
}

# Start the 24-hour test
START_TIME=$(date +%s)
DURATION=$((24*3600))  # 24 hours in seconds

echo "Starting 24-hour Wi-Fi throughput and RTT test at $(date) using server $SERVER..."

# Loop for 24 hours
while [ $(($(date +%s) - START_TIME)) -lt $DURATION ]; do
    # Test wlan0
    disable_interface "$IFACE1_NAME"
    measure_throughput_qperf "$IFACE1_NAME"
    measure_throughput_iperf3 "$IFACE1_NAME" "$IFACE1_IP"
    enable_interface "$IFACE1_NAME"

    # Wait 10 seconds
    sleep 10

    # Test wlan1
    disable_interface "$IFACE2_NAME"
    measure_throughput_qperf "$IFACE2_NAME"
    measure_throughput_iperf3 "$IFACE2_NAME" "$IFACE2_IP"
    enable_interface "$IFACE2_NAME"

    # Wait 10 seconds before repeating
    sleep 10
done

echo "24-hour test completed at $(date). Logs saved in $QPERF_LOGDIR and $IPERF_LOGDIR"
