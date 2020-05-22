#!/usr/bin/python


import os
import signal
from argparse import ArgumentParser
from subprocess import Popen, PIPE
import re
import atexit

from kafka import KafkaProducer
import json

import logging

# Logger reference
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger(__name__)

# Default IP:port used by the Kafka producer
DEFAULT_KAFKA_SERVER = 'kafka:9092'
# Kafka topic
TOPIC = 'iperf'


import grpc

# SRv6PM dependencies
import srv6pmServiceController_pb2
import srv6pmServiceController_pb2_grpc

# Controller IP and port
grpc_ip_controller = '172.16.0.100'        # TODO remove hardcoded param
grpc_port_controller = 50051        # TODO remove hardcoded param
# gRPC channel
channel = channel = grpc.insecure_channel(
    'ipv4:%s:%s' % (grpc_ip_controller, grpc_port_controller))        # TODO remove hardcoded param

PUBLISH_TO_KAFKA = False
SEND_DATA_TO_CONTROLLER = True


def publish_data_to_kafka(_from, measure_id, generator_id, data, verbose=False):
    data['from'] = _from
    data['measure_id'] = measure_id
    data['generator_id'] = generator_id
    if verbose:
        print('*** Publish data to Kafka\n')
        print('%s\n' % data)

    # Create an istance of Kafka producer
    producer = KafkaProducer(
        bootstrap_servers=DEFAULT_KAFKA_SERVER,
        security_protocol='PLAINTEXT',
        value_serializer=lambda m: json.dumps(m).encode('ascii')
    )
    # Publish measurement data to the provided topic
    result = producer.send(
        topic=TOPIC,
        value=data
    )
    # Close the producer
    producer.close()
    # Return result
    return result


def send_data_to_controller(_from, measure_id,
                            generator_id, data, verbose=False):
    data['_from'] = _from
    data['measure_id'] = measure_id
    data['generator_id'] = generator_id
    if verbose:
        print('*** Sending data to controller\n')
        print('%s\n' % data)
    # Create the gRPC request message
    request = srv6pmServiceController_pb2.SendIperfDataRequest()
    iperf_data = request.iperf_data.add()
    # From server/client
    iperf_data._from = str(_from)
    # Measure ID
    iperf_data.measure_id = int(measure_id)
    # Generator ID
    iperf_data.generator_id = int(generator_id)
    # Set interval
    iperf_data.interval.val = str(data['interval'])
    # Set bitrate
    iperf_data.bitrate.val = float(data['bitrate'])
    iperf_data.bitrate.dim = str(data['bitrate_dim'])
    # Set transfer
    iperf_data.transfer.val = float(data['transfer'])
    iperf_data.transfer.dim = str(data['transfer_dim'])
    # Set retr
    if 'retr' in data:
        iperf_data.retr.val = int(data['retr'])
    # Set cwnd
    if 'cwnd' in data:
        iperf_data.cwnd.val = float(data['cwnd'])
        iperf_data.cwnd.dim = str(data['cwnd_dim'])
    # Get the stub
    stub = srv6pmServiceController_pb2_grpc.SRv6PMControllerStub(channel)
    # Send mesaurement data
    res = stub.SendIperfData(request)
    if verbose:
        print('Sent data to the controller. Status code: %s' % res.status)


def parse_data_server(data, verbose=False):
    if verbose:
        print('Parsing line:  %s' % data)
    # Search pattern
    m = re.search(r'^\[.+]\s+(\d+.\d+-\d+.\d+)\s+sec\s+(\d+.\d+)\s(MBytes|KBytes|Mbits|Kbits|Bytes|bits)\s+(\d+.\d+)\s+((MBytes|KBytes|Mbits|Kbits|Bytes|bits)+\/sec)',
                  data)
    # Group 1.	Interval
    # Group 2.	Transfer
    # Group 3.	Transfer dimension
    # Group 4.	Bitrate
    # Group 5.	Bitrate dimension
    # Group 6.	no needed

    # Match
    if (m):
        # Extract interval
        interval = m.group(1)
        # Extract transfer
        transfer = m.group(2)
        transfer_dim = m.group(3)
        # Extract bitrate
        bitrate = m.group(4)
        bitrate_dim = m.group(5)
        # Build results dict
        res = {
            'interval': interval,
            'transfer': transfer,
            'transfer_dim': transfer_dim,
            'bitrate': bitrate,
            'bitrate_dim': bitrate_dim
        }
        if verbose:
            print('Got %s\n' % res)
        # Return results
        return res


def parse_data_client(data, verbose=False):
    if verbose:
        print('Parsing line:  %s' % data)
    # Search pattern
    m = re.search(r'^\[.+]\s+(\d+.\d+-\d+.\d+)\s+sec\s+(\d+.\d+)\s(MBytes|KBytes|Mbits|Kbits|Bytes|bits)\s+(\d+.\d+)\s+((MBytes|KBytes|Mbits|Kbits|Bytes|bits)+\/sec)\s+(\d+)\s+(\d+.\d+)\s+(MBytes|KBytes|Mbits|Kbits|Bytes|bits)',
                  data)

    # Group 1.	Interval
    # Group 2.	Transfer
    # Group 3.	Transfer dimension
    # Group 4.	Bitrate
    # Group 5.	Bitrate dimension
    # Group 6.	no needed
    # Group 7.	Retr
    # Group 8.	Cwnd
    # Group 9.	Cwnd dimension

    # Match
    if (m):
        # Extract interval
        interval = m.group(1)
        # Extract transfer
        transfer = m.group(2)
        transfer_dim = m.group(3)
        # Extract bitrate
        bitrate = m.group(4)
        bitrate_dim = m.group(5)
        # Extract retr
        retr = m.group(7)
        # Extract cwnd
        cwnd = m.group(8)
        cwnd_dim = m.group(9)
        # Build results dict
        res = {
            'interval': interval,
            'transfer': transfer,
            'transfer_dim': transfer_dim,
            'bitrate': bitrate,
            'bitrate_dim': bitrate_dim,
            'retr': retr,
            'cwnd': cwnd,
            'cwnd_dim': cwnd_dim
        }
        if verbose:
            print('Got %s\n' % res)
        # Return results
        return res


def cleanup(process):
    # Terminate iperf3 process
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    process.kill()


def start_server(address, port=None, measure_id=None,
                 generator_id=None, one_off=False, verbose=False):
    # Build the command to start the server
    cmd = 'iperf3 --forceflush --server --bind %s' % address
    # Server port
    if port is not None:
        cmd += ' --port %s' % port
    # Handle one client connection, then exit
    if one_off:
        cmd += ' --one-off'
    # Print command
    if verbose:
        print(cmd)
    # Execute the command in a new process and redirect output to PIPE
    p = Popen(cmd, shell=True, stdout=PIPE)
    # Register process termination when the python program terminates
    atexit.register(cleanup, process=p)
    # Iterate on the output generated by iperf3
    while True:
        # Read a line
        out = p.stdout.readline()
        # Check if the process has terminated
        if out == '' and p.poll() is not None:
            break
        # Parse the output generated by iperf3
        if out != '':
            # Parse data
            res = parse_data_server(out.decode(), verbose)
            if res is not None:
                # Publish data to Kafka
                if PUBLISH_TO_KAFKA:
                    publish_data_to_kafka(
                        measure_id=measure_id,
                        generator_id=generator_id,
                        res=res,
                        verbose=verbose
                    )
                # Send data to the controller
                if SEND_DATA_TO_CONTROLLER:
                    send_data_to_controller(
                        _from='server',
                        measure_id=measure_id,
                        generator_id=generator_id,
                        data=res,
                        verbose=verbose
                    )


def start_client(client_address, server_address, server_port=None,
                 duration=None, bandwidth=None, num_streams=None, mss=None,
                 bidir=False, reverse=False, zerocopy=False, version6=False,
                 measure_id=None, generator_id=None, verbose=False):
    # Build the command to start the server
    cmd = 'iperf3 --forceflush --client %s' % server_address
    # Only use IPv6
    if version6:
        cmd += ' --version6'
    # Client address
    cmd += ' --bind %s' % client_address
    # Set server port
    if server_port is not None:
        cmd += ' --port %s' % server_port
    # Time in seconds to transmit for
    if duration is not None:
        cmd += ' --time %s' % duration
    # Set target bitrate (in bits/sec)
    if bandwidth is not None:
        cmd += ' --bitrate %s' % bandwidth
    # Set TCP/SCTP maximum segment size
    if mss is not None:
        cmd += ' --set-mss %s' % mss
    # Number of parallel number of streams to run
    if num_streams is not None:
        cmd += ' --parallel %s' % num_streams
    # Define whether to run in reverse mode or not
    if reverse:
        cmd += ' --reverse'
    # Define whether to test in both directions (normal and reverse)
    if bidir:
        cmd += ' --bidir'
    # Define whether to use a 'zero copy' method of sending data,
    # such as sendfile, instead of the usual write
    if zerocopy:
        cmd += ' --zerocopy'
    # Print command
    if verbose:
        print(cmd)
    # Execute the command in a new process and redirect output to PIPE
    p = Popen(cmd, shell=True, stdout=PIPE)
    # Register process termination when the python program terminates
    atexit.register(cleanup, process=p)
    # Iterate on the output generated by iperf3
    while True:
        # Read a line
        out = p.stdout.readline()
        # Check if the process has terminated
        if out == '' and p.poll() is not None:
            break
        # Parse the output generated by iperf3
        if out != '':
            # Parse data
            res = parse_data_client(out.decode(), verbose)
            if res is not None:
                # Publish data to Kafka
                if PUBLISH_TO_KAFKA:
                    publish_data_to_kafka(
                        measure_id=measure_id,
                        generator_id=generator_id,
                        res=res,
                        verbose=verbose
                    )
                # Send data to the controller
                if SEND_DATA_TO_CONTROLLER:
                    send_data_to_controller(
                        _from='client',
                        measure_id=measure_id,
                        generator_id=generator_id,
                        data=res,
                        verbose=verbose
                    )


def parse_arguments():
    """Parse options received from command-line"""

    # Get parser
    parser = ArgumentParser(
        description='Traffic Generator'
    )
    # Run in client mode
    parser.add_argument(
        '-c', '--client', dest='host', action='store',
        default=None, help='Run in client mode, connecting to the '
        'specified server'
    )
    # Run in server mode
    parser.add_argument(
        '-s', '--server', dest='server', action='store_true',
        default=False, help='Run in server mode'
    )
    # Measure ID
    parser.add_argument(
        '--measure-id', dest='measure_id', action='store',
        help='Measure ID', required=True, type=int
    )
    # Generator ID
    parser.add_argument(
        '--generator-id', dest='generator_id', action='store',
        help='Generator ID', required=True, type=int
    )
    # Bind to the specific interface associated with the address
    parser.add_argument(
        '-B', '--bind', dest='bind', action='store',
        default=None,
        help='Bind to the specific interface associated with the address'
    )
    # Server port to listen on/connect to
    parser.add_argument(
        '-p', '--port', dest='port', action='store',
        default=None, help='Server port to listen on/connect to'
    )
    # Time in seconds to transmit for
    parser.add_argument(
        '-t', '--time', dest='time', action='store',
        default=None, help='Time in seconds to transmit for'
    )
    # Set target bitrate (in bits/sec)
    parser.add_argument(
        '-b', '--bitrate', dest='bitrate', action='store',
        default=None, help='Target bitrate'
    )
    # Set TCP/SCTP maximum segment size
    parser.add_argument(
        '-M', '--set-mss', dest='set_mss', action='store',
        default=None, help='TCP/SCTP maximum segment size'
    )
    # Number of parallel number of streams to run
    parser.add_argument(
        '-P', '--parallel', dest='parallel', action='store',
        default=None, help='Number of parallel number of streams to run'
    )
    # Define whether to run in reverse mode or not
    parser.add_argument(
        '-R', '--reverse', dest='reverse', action='store_true',
        default=False, help='Reverse the direction of a test, so that'
        'the server sends data to the client'
    )
    # Define whether to test in both directions (normal and reverse)
    parser.add_argument(
        '--bidir', dest='bidir', action='store_true',
        default=False, help='Test in both directions (normal and reverse),'
        'with both the client and the server sending and receiving data '
        'simultaneously'
    )
    # Define whether to use a 'zero copy' method of sending data,
    # such as sendfile, instead of the usual write
    parser.add_argument(
        '--zerocopy', dest='zerocopy', action='store_true',
        default=False, help='Use a zero copy method of sending data'
        'such as sendfile, instead of the usual write'
    )
    # Only use IPv6
    parser.add_argument(
        '-6', '--version6', dest='version6', action='store_true',
        default=False, help='Only use IPv6'
    )
    # Handle one client connection, then exit
    parser.add_argument(
        '-1', '--one-of', dest='one_off', action='store_true',
        default=False, help='Handle one client connection, then exit'
    )
    # Define whether to enable debug mode or not
    parser.add_argument(
        '-d', '--debug', action='store_true', help='Activate debug logs'
    )
    # Define whether to enable verbose mode or not
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Enable verbose mode'
    )
    # Parse input parameters
    args = parser.parse_args()
    # Return the arguments
    return args


if __name__ == "__main__":
    # Parse arguments
    args = parse_arguments()
    # Run in server mode
    server = args.server
    # Run in client mode
    host = args.host
    client = host is not None
    # Measure ID
    measure_id = args.measure_id
    # Generator ID
    generator_id = args.generator_id
    # Bind to the specific interface associated with the address
    bind = args.bind
    # Server port to listen on/connect to
    port = args.port
    # Time in seconds to transmit for
    time = args.time
    # Set target bitrate (in bits/sec)
    bitrate = args.bitrate
    # Set TCP/SCTP maximum segment size
    set_mss = args.set_mss
    # Number of parallel number of streams to run
    parallel = args.parallel
    # Define whether to run in reverse mode or not
    reverse = args.reverse
    # Define whether to test in both directions (normal and reverse)
    bidir = args.bidir
    # Define whether to use a 'zero copy' method of sending data,
    # such as sendfile, instead of the usual write
    zerocopy = args.zerocopy
    # Only use IPv6
    version6 = args.version6
    # Handle one client connection, then exit
    one_off = args.one_off
    # Define whether to enable debug mode or not
    debug = args.debug
    # Define whether to enable verbose mode or not
    verbose = args.verbose
    # Start server/client
    if server and client:
        print('Parameter error: cannot be both server and client')
    elif not server and not client:
        print('Parameter error: must either be a client (-c) or a server (-s)')
    elif server and not client:
        start_server(
            address=bind,
            port=port,
            one_off=one_off,
            measure_id=measure_id,
            generator_id=generator_id,
            verbose=verbose
        )
    elif client and not server:
        start_client(
            client_address=bind,
            server_address=host,
            server_port=port,
            duration=time,
            bandwidth=bitrate,
            num_streams=parallel,
            mss=set_mss,
            bidir=bidir,
            reverse=reverse,
            zerocopy=zerocopy,
            version6=version6,
            measure_id=measure_id,
            generator_id=generator_id,
            verbose=verbose
        )
    else:
        print('Invalid params')
