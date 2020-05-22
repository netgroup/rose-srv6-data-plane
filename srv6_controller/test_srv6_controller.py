#!/usr/bin/python

# General imports
import time

# SRv6PM dependencies
from srv6_controller import SRv6Controller


def start_experiment(controller):
    """Start a new experiment"""

    # Start the experiment
    controller.start_experiment(
        sender='2000::d', #'fcfd:0:0:1::1', #'2000::d',
        reflector='2000::14', #'fcfd:0:0:8::1', #'2000::14',
        send_refl_dest='fd00:0:83::2',
        refl_send_dest='fd00:0:13::2',
        send_refl_sidlist=['fcff:3::1', 'fcff:4::1', 'fcff:8::100'],
        refl_send_sidlist=['fcff:4::1', 'fcff:3::1', 'fcff:1::100'],
        send_refl_localseg='fcff:8::100',
        refl_send_localseg='fcff:1::100',
        send_in_interfaces=[],
        refl_in_interfaces=[],
        send_out_interfaces=[],
        refl_out_interfaces=[],
        measurement_protocol='TWAMP',
        send_dst_udp_port=45678,
        refl_dst_udp_port=45678,
        measurement_type='LOSS',
        authentication_mode='HMAC_SHA_256',
        authentication_key='s75pbhd-xsh;290f',
        timestamp_format='PTPv2',
        delay_measurement_mode='OneWay',
        padding_mbz=10,
        loss_measurement_mode='Inferred',
        interval_duration=10,
        delay_margin=5,  # sec assert(<interval)
        number_of_color=2,  # sec assert(==2)
        force=True
    )


def start_experiment_no_measure_id(controller):
    """Start a new experiment (without the measure_id)"""

    # Start the experiment
    controller.start_experiment(
        measure_id=100,
        sender='fcfd:0:0:1::1', #'fcff:3::1',
        reflector='fcfd:0:0:8::1', #'fcff:2::1',
        send_refl_dest='fd00:0:83::/64',
        refl_send_dest='fd00:0:13::/64',
        send_refl_sidlist=['fcff:3::1', 'fcff:8::100'],
        refl_send_sidlist=['fcff:3::1', 'fcff:1::100'],
        send_refl_localseg='fcff:8::100',
        refl_send_localseg='fcff:1::100',
        send_in_interfaces=[],
        refl_in_interfaces=[],
        send_out_interfaces=[],
        refl_out_interfaces=[],
        measurement_protocol='TWAMP',
        send_dst_udp_port=45678,
        refl_dst_udp_port=45678,
        measurement_type='LOSS',
        authentication_mode='HMAC_SHA_256',
        authentication_key='s75pbhd-xsh;290f',
        timestamp_format='PTPv2',
        delay_measurement_mode='OneWay',
        padding_mbz=10,
        loss_measurement_mode='Inferred',
        interval_duration=10,
        delay_margin=10,
        number_of_color=3
    )


def get_experiment_results(controller):
    """Get the results of a running experiment"""

    # Get the results
    results = controller.get_experiment_results(
        sender='2000::d', #'fcfd:0:0:1::1', #'2000::d',
        reflector='2000::14', #'fcfd:0:0:8::1', #'2000::14',
        send_refl_sidlist=['fcff:3::1', 'fcff:4::1', 'fcff:8::100'],
        refl_send_sidlist=['fcff:4::1', 'fcff:3::1', 'fcff:1::100'],
    )
    # Check for errors
    if results is None:
        print('Error in get_experiment_results()')
        print()
        return
    # Print the results
    for result in results:
        print("------------------------------")
        print("Measurement ID: %s" % result['measure_id'])
        print("Interval: %s" % result['interval'])
        print("Timestamp: %s" % result['timestamp'])
        print("FW Color: %s" % result['fw_color'])
        print("RV Color: %s" % result['rv_color'])
        print("sender_seq_num: %s" % result['sender_seq_num'])
        print("reflector_seq_num: %s" % result['reflector_seq_num'])
        print("Sender TX counter: %s" % result['sender_tx_counter'])
        print("Sender RX counter: %s" % result['sender_rx_counter'])
        print("Reflector TX counter: %s" % result['reflector_tx_counter'])
        print("Reflector RX counter: %s" % result['reflector_rx_counter'])
        print("------------------------------")
        print()
    print()


def stop_experiment(controller):
    """Stop a running experiment"""

    # Stop the experiment
    controller.stop_experiment(
        sender='2000::d', #'fcfd:0:0:1::1', #'2000::d',
        reflector='2000::14', #'fcfd:0:0:8::1', #'2000::14',
        send_refl_dest='fd00:0:83::2',
        refl_send_dest='fd00:0:13::2',
        send_refl_sidlist=['fcff:3::1', 'fcff:4::1', 'fcff:8::100'],
        refl_send_sidlist=['fcff:4::1', 'fcff:3::1', 'fcff:1::100'],
        send_refl_localseg='fcff:8::100',
        refl_send_localseg='fcff:1::100',
    )


# Entry point for this script
if __name__ == "__main__":
    # Enable debug mode
    debug = True
    # IP address of the gRPC server
    grpc_server_ip = '::'
    # Port of the gRPC server
    grpc_server_port = 50052
    # Port of the gRPC client
    grpc_client_port = 50052
    # Create a new SRv6 Controller
    controller = SRv6Controller(
        grpc_server_ip=grpc_server_ip,
        grpc_server_port=grpc_server_port,
        grpc_client_port=grpc_client_port,
        debug=debug
    )
    # Start a new experiment
    print()
    print()
    # start_experiment_no_measure_id(controller)
    start_experiment(controller)
    # Collects results
    for i in range(100):
        # Wait for 10 seconds
        time.sleep(10)
        # Get the results
        get_experiment_results(controller)
    # Wait for few seconds
    time.sleep(2)
    # Stop the experiment
    #stop_experiment(controller)
    print()
    print()
