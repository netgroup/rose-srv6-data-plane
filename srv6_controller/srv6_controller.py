#!/usr/bin/python

# General imports
from argparse import ArgumentParser
import logging
import time
import grpc_client

# SRv6PM dependencies
import srv6pmCommons_pb2


# Global variables definition
#
#
# Logger reference
logger = logging.getLogger(__name__)
# Default parameters for SRv6 controller
#
# Default port of the gRPC server
DEFAULT_GRPC_PORT = 12345
# Define wheter to use SSL or not
DEFAULT_SECURE = False
# SSL certificate of the root CA
DEFAULT_CERTIFICATE = 'client_cert.pem'


# Python class representing a SRv6 controller
class SRv6Controller:
    """
    A class used to represent a SRv6 Controller

    ...

    Attributes
    ----------
    grpc_port : int
        The port of the gRPC server
    secure : bool
        Define wheter to use SSL or not to communicate with the gRPC server
        (default is False)
    certificate : str
        The path of the CA root certificate required for the SSL
        (default is None)
    debug : bool
        Define wheter to enable debug mode or not (default is False)

    Methods
    -------
    start_experiment(send_ip, refl_ip, send_dest, refl_dest, send_sidlist,
                     refl_sidlist, send_in_interfaces, refl_in_interfaces,
                     send_out_interfaces, refl_out_interfaces,
                     measurement_protocol, send_dst_udp_port,
                     refl_dst_udp_port, measurement_type, authentication_mode,
                     authentication_key, timestamp_format,
                     delay_measurement_mode, padding_mbz,
                     loss_measurement_mode, interval_duration, delay_margin,
                     number_of_color, measure_id=None, send_localseg=None,
                     refl_localseg=None)
        Start an experiment
    """

    def __init__(self, grpc_port, secure=False, certificate=None, debug=False):
        """
        Parameters
        ----------
        grpc_port : int
            the port of the gRPC server
        secure : bool
            define wheter to use SSL or not to communicate with the gRPC server
            (default is False)
        certificate : str
            the path of the CA root certificate required for the SSL
            (default is None)
        debug : bool
            define wheter to enable debug mode or not (default is False)
        """

        # Port of the gRPC server
        self.grpc_port = grpc_port
        # Measure ID
        self.measure_id = -1
        # gRPC secure mode
        self.secure = secure
        # SSL certificate of the root CA required for gRPC secure mode
        self.certificate = certificate
        # Debug mode
        self.debug = debug
        # Mapping IP address to gRPC channels
        self.grpc_channels = dict()

    def get_grpc_channel(self, ip_address):
        # Get the gRPC channel of the node
        channel = None
        if ip_address in self.grpc_channels:
            # gRPC channel already opened, we can use it
            channel = self.grpc_channels[ip_address]
        else:
            # Get a new gRPC channel for the node
            channel = grpc_client.get_grpc_session(
                ip_address, self.grpc_port, self.secure, self.certificate)
            # Add channel to mapping
            self.grpc_channels[ip_address] = channel
        # Return the channel
        return channel

    def _create_uni_srv6_path(self, ingress, egress,
                              destination, segments, localseg=None):
        """ Create a unidirectional SRv6 tunnel from <ingress> to <egress>

        Parameters
        ----------
        ingress : str
            The IP address of the ingress node
        egress : str
            The IP address of the egress node
        destination : str
            The destination prefix of the SRv6 path.
            It can be a IP address or a subnet.
        segments : list
            The SID list to be applied to the packets going to the destination
        localseg : str, optional
            The local segment to be associated to the End.DT6 seg6local
            function on the egress node.
            If the argument 'localseg' isn't passed in, the End.DT6 function
            is not created.
        """

        # Get the gRPC channel of the ingress node
        ingress_channel = self.get_grpc_channel(ingress)
        # Get the gRPC channel of the egress node
        egress_channel = self.get_grpc_channel(egress)
        # Add seg6 route to <ingress> to steer the packets sent to the
        # <destination> through the SID list <segments>
        #
        # Equivalent to the command:
        #    ingress: ip -6 route add <destination> encap seg6 mode encap \
        #            segs <segments> dev <device>
        grpc_client.add_srv6_path(
            channel=ingress_channel,
            destination=destination,
            segments=segments
        )
        # Perform "Decapsulaton and Specific IPv6 Table Lookup" function
        # on the egress node <egress>
        # The decap function is associated to the <localseg> passed in
        # as argument. If argument 'localseg' isn't passed in, the behavior
        # is not added
        #
        # Equivalent to the command:
        #    egress: ip -6 route add <localseg> encap seg6local action \
        #            End.DT6 table 254 dev <device>
        if localseg is not None:
            grpc_client.add_srv6_behavior(
                channel=egress_channel,
                segment=localseg,
                action='End.DT6',
                table=254
            )

    def create_srv6_path(self, node_l, node_r,
                         sidlist_lr, sidlist_rl, dest_lr, dest_rl,
                         localseg_lr=None, localseg_rl=None):
        """Create a bidirectional SRv6 tunnel.

        Parameters
        ----------
        node_l : str
            The IP address of the left endpoint of the SRv6 tunnel
        node_r : str
            The IP address of the right endpoint of the SRv6 tunnel
        sidlist_lr : list
            The SID list to be installed on the packets going
            from <node_l> to <node_r>
        sidlist_rl : list
            SID list to be installed on the packets going
            from <node_r> to <node_l>
        dest_lr : str
            The destination prefix of the SRv6 path from <node_l> to <node_r>.
            It can be a IP address or a subnet.
        dest_rl : str
            The destination prefix of the SRv6 path from <node_r> to <node_l>.
            It can be a IP address or a subnet.
        localseg_lr : str, optional
            The local segment to be associated to the End.DT6 seg6local
            function for the SRv6 path from <node_l> to <node_r>.
            If the argument 'localseg_l' isn't passed in, the End.DT6 function
            is not created.
        localseg_rl : str, optional
            The local segment to be associated to the End.DT6 seg6local
            function for the SRv6 path from <node_r> to <node_l>.
            If the argument 'localseg_r' isn't passed in, the End.DT6 function
            is not created.
        """

        # Create a unidirectional SRv6 tunnel from <node_l> to <node_r>
        self._create_uni_srv6_path(
            ingress=node_l,
            egress=node_r,
            destination=dest_lr,
            segments=sidlist_lr,
            localseg=localseg_lr
        )
        # Create a unidirectional SRv6 tunnel from <node_r> to <node_l>
        self._create_uni_srv6_path(
            ingress=node_r,
            egress=node_l,
            destination=dest_rl,
            segments=sidlist_rl,
            localseg=localseg_rl
        )

    def _destroy_uni_srv6_path(self, ingress, egress,
                               destination, localseg=None):
        """Destroy a unidirectional SRv6 tunnel from <ingress> to <egress>

        Parameters
        ----------

        Parameters
        ----------
        ingress : str
            The IP address of the ingress node
        egress : str
            The IP address of the egress node
        destination : str
            The destination prefix of the SRv6 path.
            It can be a IP address or a subnet.
        localseg : str, optional
            The local segment associated to the End.DT6 seg6local
            function on the egress node.
            If the argument 'localseg' isn't passed in, the End.DT6 function
            is not removed.
        """

        # Get the gRPC channel of the ingress node
        ingress_channel = self.get_grpc_channel(ingress)
        # Get the gRPC channel of the egress node
        egress_channel = self.get_grpc_channel(egress)
        # Remove seg6 route from <ingress> to steer the packets sent to
        # <destination> through the SID list <segments>
        #
        # Equivalent to the command:
        #    ingress: ip -6 route del <destination> encap seg6 mode encap \
        #             segs <segments> dev <device>
        grpc_client.remove_srv6_path(
            channel=ingress_channel,
            destination=destination
        )
        # Remove "Decapsulaton and Specific IPv6 Table Lookup" function
        # from the egress node <egress>
        # The decap function associated to the <localseg> passed in
        # as argument. If argument 'localseg' isn't passed in, the behavior
        # is not removed
        #
        # Equivalent to the command:
        #    egress: ip -6 route del <localseg> encap seg6local action \
        #            End.DT6 table 254 dev <device>
        if localseg is not None:
            grpc_client.remove_srv6_behavior(
                channel=egress_channel,
                segment=localseg
            )

    def destroy_srv6_path(self, node_l, node_r,
                          dest_lr, dest_rl, localseg_lr, localseg_rl):
        """Destroy a bidirectional SRv6 tunnel

        Parameters
        ----------
        node_l_channel : <gRPC channel>
            The gRPC channel of the left endpoint of the SRv6 tunnel
        node_r_channel : <gRPC channel>
            The gRPC channel of the right endpoint of the SRv6 tunnel
        node_l : str
            The IP address of the left endpoint of the SRv6 tunnel
        node_r : str
            The IP address of the right endpoint of the SRv6 tunnel
        dest_lr : str
            The destination prefix of the SRv6 path from <node_l> to <node_r>.
            It can be a IP address or a subnet.
        dest_rl : str
            The destination prefix of the SRv6 path from <node_r> to <node_l>.
            It can be a IP address or a subnet.
        localseg_lr : str, optional
            The local segment associated to the End.DT6 seg6local
            function for the SRv6 path from <node_l> to <node_r>.
            If the argument 'localseg_l' isn't passed in, the End.DT6 function
            is not removed.
        localseg_rl : str, optional
            The local segment associated to the End.DT6 seg6local
            function for the SRv6 path from <node_r> to <node_l>.
            If the argument 'localseg_r' isn't passed in, the End.DT6 function
            is not removed.
        """

        # Create a unidirectional SRv6 tunnel from <node_l> to <node_r>
        self._destroy_uni_srv6_path(
            ingress=node_l,
            egress=node_r,
            destination=dest_lr,
            localseg=localseg_lr
        )
        # Create a unidirectional SRv6 tunnel from <node_r> to <node_l>
        self._destroy_uni_srv6_path(
            ingress=node_r,
            egress=node_l,
            destination=dest_rl,
            localseg=localseg_rl
        )

    # Start the measurement process
    def start_measurement(self, measure_id, sender, reflector,
                          send_refl_sidlist, refl_send_sidlist,
                          send_in_interfaces, refl_in_interfaces,
                          send_out_interfaces, refl_out_interfaces,
                          measurement_protocol, send_dst_udp_port,
                          refl_dst_udp_port, measurement_type,
                          authentication_mode, authentication_key,
                          timestamp_format, delay_measurement_mode,
                          padding_mbz, loss_measurement_mode,
                          interval_duration, delay_margin, number_of_color):

        # Get the gRPC channel of the sender
        send_channel = self.get_grpc_channel(sender)
        # Get the gRPC channel of the reflector
        refl_channel = self.get_grpc_channel(reflector)
        print("\n************** Start Measurement **************\n")
        # Start the experiment on the reflector
        refl_res = grpc_client.startExperimentReflector(
            channel=refl_channel,
            in_sidlist=send_refl_sidlist,
            out_sidlist=refl_send_sidlist,
            in_interfaces=refl_in_interfaces,
            out_interfaces=refl_out_interfaces,
            measurement_protocol=measurement_protocol,
            dst_udp_port=refl_dst_udp_port,
            measurement_type=measurement_type,
            authentication_mode=authentication_mode,
            authentication_key=authentication_key,
            loss_measurement_mode=loss_measurement_mode,
            interval_duration=interval_duration,
            delay_margin=delay_margin,
            number_of_color=number_of_color
        )
        if refl_res is not None and \
                refl_res.status == srv6pmCommons_pb2.STATUS_SUCCESS:
            print("Started Measure Reflector RES: %s" % refl_res.status)
        else:
            print("ERROR startExperimentReflector  RES: %s" % refl_res)
        # Start the experiment on the sender
        sender_res = grpc_client.startExperimentSender(
            channel=send_channel,
            in_sidlist=refl_send_sidlist,
            out_sidlist=send_refl_sidlist,
            in_interfaces=send_in_interfaces,
            out_interfaces=send_out_interfaces,
            measurement_protocol=measurement_protocol,
            dst_udp_port=send_dst_udp_port,
            measurement_type=measurement_type,
            authentication_mode=authentication_mode,
            authentication_key=authentication_key,
            timestamp_format=timestamp_format,
            delay_measurement_mode=delay_measurement_mode,
            padding_mbz=padding_mbz,
            loss_measurement_mode=loss_measurement_mode,
            interval_duration=interval_duration,
            delay_margin=delay_margin,
            number_of_color=number_of_color
        )
        if sender_res is not None and \
                sender_res.status == srv6pmCommons_pb2.STATUS_SUCCESS:
            print("Started Measure Sender RES: %s" % sender_res.status)
        else:
            print("ERROR startExperimentSender  RES: %s" % sender_res)

    def get_measurement_results(self, sender, reflector,
                                send_refl_sidlist, refl_send_sidlist):
        # Get the gRPC channel of the sender
        send_channel = self.get_grpc_channel(sender)
        # Get the gRPC channel of the reflector
        refl_channel = self.get_grpc_channel(reflector)
        # Retrieve the results of the experiment
        print("\n************** Get Measurement Data **************\n")
        # Retrieve the results from the sender
        sender_res = grpc_client.retriveExperimentResultsSender(
            channel=send_channel,
            sidlist=send_refl_sidlist
        )
        # Collect the results
        res = None
        if sender_res is not None:
            print("Received Data Sender RES: %s" % sender_res.status)
            res = list()
            for data in sender_res.measurement_data:
                res.append({
                    'measure_id': data.measure_id,
                    'interval': data.interval,
                    'timestamp': data.timestamp,
                    'color': data.color,
                    'sender_tx_counter': data.sender_tx_counter,
                    'sender_rx_counter': data.sender_rx_counter,
                    'reflector_tx_counter': data.reflector_tx_counter,
                    'reflector_rx_counter': data.reflector_rx_counter,
                })
        else:
            print("ERROR retriveExperimentResultsSender RES: %s" % sender_res)
        return res

    def stop_measurement(self, sender, reflector,
                         send_refl_sidlist, refl_send_sidlist):
        # Get the gRPC channel of the sender
        send_channel = self.get_grpc_channel(sender)
        # Get the gRPC channel of the reflector
        refl_channel = self.get_grpc_channel(reflector)
        print("\n************** Stop Measurement **************\n")
        # Stop the experiment on the sender
        refl_res = grpc_client.stopExperimentSender(
            channel=send_channel,
            sidlist=send_refl_sidlist
        )
        if refl_res is not None and \
                refl_res.status == srv6pmCommons_pb2.STATUS_SUCCESS:
            print("Stopped Measure RES: %s" % refl_res.status)
        else:
            print("ERROR startExperimentSender RES: %s" % refl_res)
        # Stop the experiment on the reflector
        sender_res = grpc_client.stopExperimentReflector(
            channel=refl_channel,
            sidlist=refl_send_sidlist
        )
        if sender_res is not None and \
                sender_res.status == srv6pmCommons_pb2.STATUS_SUCCESS:
            print("Stopped Measure RES: %s" % sender_res.status)
        else:
            print("ERROR startExperimentSender RES: %s" % sender_res)

    def start_experiment(self, sender, reflector, send_refl_dest,
                         refl_send_dest, send_refl_sidlist, refl_send_sidlist,
                         send_in_interfaces, refl_in_interfaces,
                         send_out_interfaces, refl_out_interfaces,
                         measurement_protocol, send_dst_udp_port,
                         refl_dst_udp_port, measurement_type,
                         authentication_mode, authentication_key,
                         timestamp_format, delay_measurement_mode,
                         padding_mbz, loss_measurement_mode,
                         interval_duration, delay_margin,
                         number_of_color, measure_id=None,
                         send_refl_localseg=None, refl_send_localseg=None):
        """Start an experiment.

        Parameters
        ----------
        sender : str
            The IP address of the sender node
        reflector : str
            The IP address of the reflector node
        send_refl_dest : str
            The destination of the SRv6 path on the sender
        refl_send_dest : str
            The destination of the SRv6 path on the reflector
        send_refl_sidlist : list
            The SID list to be used by the sender
        refl_send_sidlist : list
            The SID list to be used by the reflector
        send_in_interfaces : list
            The list of the incoming interfaces of the sender
        refl_in_interfaces : list
            The list of the incoming interfaces of the reflector
        send_out_interfaces : list
            The list of the outgoing interfaces of the sender
        refl_out_interfaces : list
            The list of the outgoing interfaces of the reflector
        measurement_protocol : str
            The measurement protocol (i.e. TWAMP or STAMP)
        send_dst_udp_port : int
            The destination UDP port used by the sender
        refl_dst_udp_port : int
            The destination UDP port used by the reflector
        measurement_type : str
            The measurement type (i.e. delay or loss)
        authentication_mode : str
            The authentication mode (i.e. HMAC_SHA_256)
        authentication_key : str
            The authentication key
        timestamp_format : str
            The Timestamp Format (i.e. PTPv2 or NTP)
        delay_measurement_mode : str
            Delay measurement mode (i.e. one-way, two-way or loopback mode)
        padding_mbz : int
            The padding size
        loss_measurement_mode : str
            The loss measurement mode (i.e. Inferred or Direct mode)
        interval_duration : int
            The duration of the interval
        delay_margin : int
            The delay margin
        number_of_color : int
            The number of the color
        measure_id : int, optional
            Identifier for the experiment (default is None).
            If the argument 'measure_id' isn't passed in, the measure_id is
            automatically generated.
        send_refl_localseg=None : str, optional
            The local segment associated to the End.DT6 function on the sender
            (default is None).
            If the argument 'send_localseg' isn't passed in, the seg6local
            End.DT6 route is not created.
        refl_send_localseg=None : str, optional
            The local segment associated to the End.DT6 function on the
            reflector (default is None).
            If the argument 'send_localseg' isn't passed in, the seg6local
            End.DT6 route is not created.
        """

        # Get a new measure ID, if it isn't passed in as argument
        if measure_id is None:
            self.measure_id += 1
            measure_id = self.measure_id
        # Create a bidirectional SRv6 tunnel between the sender and the
        # reflector
        self.create_srv6_path(
            node_l=sender,
            node_r=reflector,
            dest_lr=send_refl_dest,
            dest_rl=refl_send_dest,
            localseg_lr=send_refl_localseg,
            localseg_rl=refl_send_localseg,
            sidlist_lr=send_refl_sidlist,
            sidlist_rl=refl_send_sidlist
        )
        # Start measurement process
        self.start_measurement(
            measure_id=measure_id,
            sender=sender,
            reflector=reflector,
            send_refl_sidlist=send_refl_sidlist,
            refl_send_sidlist=refl_send_sidlist,
            send_in_interfaces=send_in_interfaces,
            send_out_interfaces=send_out_interfaces,
            refl_in_interfaces=refl_in_interfaces,
            refl_out_interfaces=refl_out_interfaces,
            measurement_protocol=measurement_protocol,
            send_dst_udp_port=send_dst_udp_port,
            refl_dst_udp_port=refl_dst_udp_port,
            measurement_type=measurement_type,
            authentication_mode=authentication_mode,
            authentication_key=authentication_key,
            timestamp_format=timestamp_format,
            delay_measurement_mode=delay_measurement_mode,
            padding_mbz=padding_mbz,
            loss_measurement_mode=loss_measurement_mode,
            interval_duration=interval_duration,
            delay_margin=delay_margin,
            number_of_color=number_of_color
        )

    def get_experiment_results(self, sender, reflector,
                               send_refl_sidlist, refl_send_sidlist):
        """Get the results of an experiment."""

        # Get the results
        return self.get_measurement_results(
            sender=sender,
            reflector=reflector,
            send_refl_sidlist=send_refl_sidlist,
            refl_send_sidlist=refl_send_sidlist
        )

    def stop_experiment(self, sender, reflector, send_refl_dest,
                        refl_send_dest, send_refl_sidlist, refl_send_sidlist,
                        send_refl_localseg=None, refl_send_localseg=None):
        """Stop a running experiment."""

        # Stop the experiment
        self.stop_measurement(
            sender=sender,
            reflector=reflector,
            send_refl_sidlist=send_refl_sidlist,
            refl_send_sidlist=refl_send_sidlist
        )
        # Remove the SRv6 path
        self.destroy_srv6_path(
            node_l=sender,
            node_r=reflector,
            dest_lr=send_refl_dest,
            dest_rl=refl_send_dest,
            localseg_lr=send_refl_localseg,
            localseg_rl=refl_send_localseg
        )


# Parse options
def parse_arguments():
    # Get parser
    parser = ArgumentParser(
        description='SRv6 Controller'
    )
    # Port of the gRPC server
    parser.add_argument(
        '-p', '--grpc-port', dest='grpc_port', action='store',
        default=DEFAULT_GRPC_PORT, help='Port of the gRPC server'
    )
    # Define wheter to use SSL or not
    parser.add_argument(
        '-s', '--secure', action='store_true',
        help='Activate secure mode', default=DEFAULT_SECURE
    )
    # SSL certificate of the root CA
    parser.add_argument(
        '-c', '--client-cert', dest='client_cert', action='store',
        default=DEFAULT_CERTIFICATE, help='Client certificate file'
    )
    # Define wheter to enable debug mode or not
    parser.add_argument(
        '-d', '--debug', action='store_true', help='Activate debug logs'
    )
    # Parse input parameters
    args = parser.parse_args()
    # Return the arguments
    return args


# Entry point for this script
if __name__ == "__main__":
    # Process command-line arguments
    args = parse_arguments()
    # gRPC server port
    # We assume that the same port is used
    # by all the gRPC server
    grpc_port = args.grpc_port
    # Setup properly the secure mode
    secure = args.secure
    # SSL certificate of the root CA required for gRPC secure mode
    certificate = args.client_cert
    # Setup properly the logger
    if args.debug:
        logger.setLevel(level=logging.DEBUG)
    else:
        logger.setLevel(level=logging.INFO)
    # Debug settings
    server_debug = logger.getEffectiveLevel() == logging.DEBUG
    logger.info('SERVER_DEBUG:' + str(server_debug))
    # Test controller
    controller = SRv6Controller(12345)
    controller.start_experiment(
        sender='fcff:3::1',
        reflector='fcff:2::1',
        send_refl_dest='fd00:0:32::/64',
        refl_send_dest='fd00:0:23::/64',
        send_refl_sidlist=['fcff:2::1', 'fcff:2::100'],
        refl_send_sidlist=['fcff:3::1', 'fcff:3::100'],
        send_refl_localseg='fcff:2::100',
        refl_send_localseg='fcff:3::100',
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
    time.sleep(10)
    controller.get_experiment_results(
        sender='fcff:3::1',
        reflector='fcff:2::1',
        send_refl_sidlist=['fcff:2::1', 'fcff:2::100'],
        refl_send_sidlist=['fcff:3::1', 'fcff:3::100']
    )
