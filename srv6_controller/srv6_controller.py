#!/usr/bin/python

# General imports
from argparse import ArgumentParser
from concurrent import futures
from threading import Thread
import grpc
import logging
import time
import grpc_client

# SRv6PM dependencies
import srv6pmCommons_pb2
import srv6pmServiceController_pb2_grpc
import srv6pmServiceController_pb2


# Global variables definition
#
#
# Logger reference
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger(__name__)
# Default parameters for SRv6 controller
#
# Default IP address of the gRPC server
DEFAULT_GRPC_SERVER_IP = '::'
# Default port of the gRPC server
DEFAULT_GRPC_SERVER_PORT = 12345
# Default port of the gRPC client
DEFAULT_GRPC_CLIENT_PORT = 12345
# Define whether to use SSL or not for the gRPC client
DEFAULT_CLIENT_SECURE = False
# SSL certificate of the root CA
DEFAULT_CLIENT_CERTIFICATE = 'client_cert.pem'
# Define whether to use SSL or not for the gRPC server
DEFAULT_SERVER_SECURE = False
# SSL certificate of the gRPC server
DEFAULT_SERVER_CERTIFICATE = 'server_cert.pem'
# SSL key of the gRPC server
DEFAULT_SERVER_KEY = 'server_cert.pem'


# Human-readable gRPC return status
status_code_to_str = {
    srv6pmCommons_pb2.STATUS_SUCCESS: 'Success',
    srv6pmCommons_pb2.STATUS_OPERATION_NOT_SUPPORTED: 'Operation not supported',
    srv6pmCommons_pb2.STATUS_BAD_REQUEST: 'Bad request',
    srv6pmCommons_pb2.STATUS_INTERNAL_ERROR: 'Internal error',
    srv6pmCommons_pb2.STATUS_INVALID_GRPC_REQUEST: 'Invalid gRPC request',
    srv6pmCommons_pb2.STATUS_FILE_EXISTS: 'An entity already exists',
    srv6pmCommons_pb2.STATUS_NO_SUCH_PROCESS: 'Entity not found',
    srv6pmCommons_pb2.STATUS_INVALID_ACTION: 'Invalid seg6local action',
    srv6pmCommons_pb2.STATUS_GRPC_SERVICE_UNAVAILABLE: 'gRPC service not available',
    srv6pmCommons_pb2.STATUS_GRPC_UNAUTHORIZED: 'Unauthorized'
}


# Python class representing a SRv6 controller
class SRv6Controller():
    """
    A class used to represent a SRv6 Controller

    ...

    Attributes
    ----------
    grpc_server_ip : str
        the IP address of the gRPC server
    grpc_server_port : int
        the port of the gRPC server
    grpc_client_port : int
        the port of the gRPC client
    grpc_client_secure : bool
        define whether to use SSL or not to communicate with the gRPC server
        (default is False)
    grpc_client_certificate : str
        the path of the CA root certificate required for the SSL
        (default is None)
    grpc_server_secure : bool
        define whether to use SSL or not for the gRPC server
        (default is False)
    grpc_server_certificate : str
        the path of the server certificate required for the SSL
        (default is None)
    grpc_server_key : str
        the path of the server key required for the SSL
        (default is None)
    debug : bool
        Define whether to enable debug mode or not (default is False)

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

    get_experiment_results(sender, reflector,
                           send_refl_sidlist, refl_send_sidlist)
        Get the results of a running experiment

    stop_experiment(sender, reflector, send_refl_dest,
                    refl_send_dest, send_refl_sidlist, refl_send_sidlist,
                    send_refl_localseg=None, refl_send_localseg=None)
        Stop a running experiment
    """

    def __init__(self, grpc_server_ip, grpc_server_port, grpc_client_port,
                 grpc_client_secure=False, grpc_client_certificate=None,
                 grpc_server_secure=False, grpc_server_certificate=None,
                 grpc_server_key=None, debug=False):
        """
        Parameters
        ----------
        grpc_server_ip : str
            the IP address of the gRPC server
        grpc_server_port : int
            the port of the gRPC server
        grpc_client_port : int
            the port of the gRPC client
        grpc_client_secure : bool
            define whether to use SSL or not to communicate with the gRPC server
            (default is False)
        grpc_client_certificate : str
            the path of the CA root certificate required for the SSL
            (default is None)
        grpc_server_secure : bool
            define whether to use SSL or not for the gRPC server
            (default is False)
        grpc_server_certificate : str
            the path of the server certificate required for the SSL
            (default is None)
        grpc_server_key : str
            the path of the server key required for the SSL
            (default is None)
        debug : bool
            define whether to enable debug mode or not (default is False)
        """

        logger.info('Initializing SRv6 controller')
        # Port of the gRPC client
        self.grpc_client_port = grpc_client_port
        # Measure ID
        self.measure_id = -1
        # gRPC secure mode
        self.grpc_client_secure = grpc_client_secure
        # SSL certificate of the root CA required for gRPC secure mode
        self.grpc_client_certificate = grpc_client_certificate
        # Debug mode
        self.debug = debug
        # Setup properly the logger
        if self.debug:
            logger.setLevel(level=logging.DEBUG)
        else:
            logger.setLevel(level=logging.INFO)
        # Mapping IP address to gRPC channels
        self.grpc_channels = dict()
        # Start the gRPC server
        # This is a blocking operation, so we need to execute it
        # in a separated thread
        kwargs = {
            'grpc_ip': grpc_server_ip,
            'grpc_port': grpc_server_port,
            'secure': grpc_server_secure,
            'key': grpc_server_key,
            'certificate': grpc_server_certificate
        }
        Thread(target=self.__start_grpc_server, kwargs=kwargs).start()
        time.sleep(1)

    def __get_grpc_session(self, ip_address):
        """Create a Channel to a server. If a previously opened channel
           already exists, return it instead of creating a new one.

        Parameters
        ----------
        ip_address : str
            The IP address of the gRPC server
        """

        # Get the gRPC channel of the node
        channel = None
        if ip_address in self.grpc_channels:
            # gRPC channel already opened, we can use it
            channel = self.grpc_channels[ip_address]
        else:
            # Get a new gRPC channel for the node
            channel = grpc_client.get_grpc_session(
                ip_address, self.grpc_client_port,
                self.grpc_client_secure, self.grpc_client_certificate)
            # Add channel to mapping
            self.grpc_channels[ip_address] = channel
        # Return the channel
        return channel

    def __print_status_message(self, status_code, success_msg, failure_msg):
        """Print success or failure message depending of the status code
           returned by a gRPC operation.

        Parameters
        ----------
        status_code : int
            The status code returned by the gRPC operation
        success_msg : str
            The message to print in case of success
        failure_msg : str
            The message to print in case of error
        """

        if status_code == srv6pmCommons_pb2.STATUS_SUCCESS:
            # Success
            print('%s (status code %s - %s)'
                  % (success_msg, status_code,
                     status_code_to_str.get(status_code, 'Unknown')))
        else:
            # Error
            print('%s (status code %s - %s)'
                  % (failure_msg, status_code,
                     status_code_to_str.get(status_code, 'Unknown')))

    def __create_uni_srv6_path(self, ingress, egress,
                               destination, segments, localseg=None):
        """Create a unidirectional SRv6 tunnel from <ingress> to <egress>

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
        ingress_channel = self.__get_grpc_session(ingress)
        # Get the gRPC channel of the egress node
        egress_channel = self.__get_grpc_session(egress)
        # Add seg6 route to <ingress> to steer the packets sent to the
        # <destination> through the SID list <segments>
        #
        # Equivalent to the command:
        #    ingress: ip -6 route add <destination> encap seg6 mode encap \
        #            segs <segments> dev <device>
        res = grpc_client.add_srv6_path(
            channel=ingress_channel,
            destination=destination,
            segments=segments
        )
        # Pretty print status code
        self.__print_status_message(
            status_code=res,
            success_msg='Added SRv6 Path',
            failure_msg='Error in add_srv6_path()'
        )
        # If an error occurred, abort the operation
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
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
            res = grpc_client.add_srv6_behavior(
                channel=egress_channel,
                segment=localseg,
                action='End.DT6',
                table=254
            )
            # Pretty print status code
            self.__print_status_message(
                status_code=res,
                success_msg='Added SRv6 Behavior',
                failure_msg='Error in add_srv6_behavior()'
            )
            # If an error occurred, abort the operation
            if res != srv6pmCommons_pb2.STATUS_SUCCESS:
                return res
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    def __create_srv6_path(self, node_l, node_r,
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
        res = self.__create_uni_srv6_path(
            ingress=node_l,
            egress=node_r,
            destination=dest_lr,
            segments=sidlist_lr,
            localseg=localseg_lr
        )
        # If an error occurred, abort the operation
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Create a unidirectional SRv6 tunnel from <node_r> to <node_l>
        res = self.__create_uni_srv6_path(
            ingress=node_r,
            egress=node_l,
            destination=dest_rl,
            segments=sidlist_rl,
            localseg=localseg_rl
        )
        # If an error occurred, abort the operation
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    def __destroy_uni_srv6_path(self, ingress, egress, destination,
                                localseg=None, ignore_errors=False):
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
        ignore_errors : bool, optional
            Whether to ignore "No such process" errors or not (default is False)
        """

        # Get the gRPC channel of the ingress node
        ingress_channel = self.__get_grpc_session(ingress)
        # Get the gRPC channel of the egress node
        egress_channel = self.__get_grpc_session(egress)
        # Remove seg6 route from <ingress> to steer the packets sent to
        # <destination> through the SID list <segments>
        #
        # Equivalent to the command:
        #    ingress: ip -6 route del <destination> encap seg6 mode encap \
        #             segs <segments> dev <device>
        res = grpc_client.remove_srv6_path(
            channel=ingress_channel,
            destination=destination
        )
        # Pretty print status code
        self.__print_status_message(
            status_code=res,
            success_msg='Removed SRv6 Path',
            failure_msg='Error in remove_srv6_path()'
        )
        # If an error occurred, abort the operation
        if res == srv6pmCommons_pb2.STATUS_NO_SUCH_PROCESS:
            # If the 'ignore_errors' flag is set, continue
            if not ignore_errors:
                return res
        elif res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
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
            res = grpc_client.remove_srv6_behavior(
                channel=egress_channel,
                segment=localseg
            )
            # Pretty print status code
            self.__print_status_message(
                status_code=res,
                success_msg='Removed SRv6 behavior',
                failure_msg='Error in remove_srv6_behavior()'
            )
            # If an error occurred, abort the operation
            if res == srv6pmCommons_pb2.STATUS_NO_SUCH_PROCESS:
                # If the 'ignore_errors' flag is set, continue
                if not ignore_errors:
                    return res
            elif res != srv6pmCommons_pb2.STATUS_SUCCESS:
                return res
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    def __destroy_srv6_path(self, node_l, node_r,
                            dest_lr, dest_rl, localseg_lr, localseg_rl,
                            ignore_errors=False):
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
        ignore_errors : bool, optional
            Whether to ignore "No such process" errors or not (default is False)
        """

        # Remove unidirectional SRv6 tunnel from <node_l> to <node_r>
        res = self.__destroy_uni_srv6_path(
            ingress=node_l,
            egress=node_r,
            destination=dest_lr,
            localseg=localseg_lr,
            ignore_errors=ignore_errors
        )
        # If an error occurred, abort the operation
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Remove unidirectional SRv6 tunnel from <node_r> to <node_l>
        res = self.__destroy_uni_srv6_path(
            ingress=node_r,
            egress=node_l,
            destination=dest_rl,
            localseg=localseg_rl,
            ignore_errors=ignore_errors
        )
        # If an error occurred, abort the operation
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    # Start the measurement process
    def __start_measurement(self, measure_id, sender, reflector,
                            send_refl_sidlist, refl_send_sidlist,
                            send_in_interfaces, refl_in_interfaces,
                            send_out_interfaces, refl_out_interfaces,
                            measurement_protocol, send_dst_udp_port,
                            refl_dst_udp_port, measurement_type,
                            authentication_mode, authentication_key,
                            timestamp_format, delay_measurement_mode,
                            padding_mbz, loss_measurement_mode,
                            interval_duration, delay_margin, number_of_color):
        """Start the measurement process on reflector and sender.

        Parameters
        ----------
        measure_id : int
            Identifier for the experiment
        sender : str
            The IP address of the sender node
        reflector : str
            The IP address of the reflector node
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
        """

        # Get the gRPC channel of the sender
        send_channel = self.__get_grpc_session(sender)
        # Get the gRPC channel of the reflector
        refl_channel = self.__get_grpc_session(reflector)
        print("\n************** Start Measurement **************\n")
        # Start the experiment on the reflector
        refl_res = grpc_client.startExperimentReflector(
            channel=refl_channel,
            sidlist=send_refl_sidlist,
            rev_sidlist=refl_send_sidlist,
            in_interfaces=refl_in_interfaces,
            out_interfaces=refl_out_interfaces,
            measurement_protocol=measurement_protocol,
            send_udp_port=send_dst_udp_port,
            refl_udp_port=refl_dst_udp_port,
            measurement_type=measurement_type,
            authentication_mode=authentication_mode,
            authentication_key=authentication_key,
            loss_measurement_mode=loss_measurement_mode,
            interval_duration=interval_duration,
            delay_margin=delay_margin,
            number_of_color=number_of_color
        )
        # Pretty print status code
        self.__print_status_message(
            status_code=refl_res.status,
            success_msg='Started Measure Reflector',
            failure_msg='Error in startExperimentReflector()'
        )
        # Check for errors
        if refl_res.status != srv6pmCommons_pb2.STATUS_SUCCESS:
            return refl_res.status
        # Start the experiment on the sender
        sender_res = grpc_client.startExperimentSender(
            channel=send_channel,
            sidlist=send_refl_sidlist,
            rev_sidlist=refl_send_sidlist,
            in_interfaces=send_in_interfaces,
            out_interfaces=send_out_interfaces,
            measurement_protocol=measurement_protocol,
            send_udp_port=send_dst_udp_port,
            refl_udp_port=refl_dst_udp_port,
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
        # Pretty print status code
        self.__print_status_message(
            status_code=sender_res.status,
            success_msg='Started Measure Sender',
            failure_msg='Error in startExperimentSender()'
        )
        # Check for errors
        if sender_res.status != srv6pmCommons_pb2.STATUS_SUCCESS:
            return sender_res.status
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    def __get_measurement_results(self, sender, reflector,
                                send_refl_sidlist, refl_send_sidlist):
        """Get the results of a measurement process.

        Parameters
        ----------
        sender : str
            The IP address of the sender node
        reflector : str
            The IP address of the reflector node
        send_refl_sidlist : list
            The SID list used by the sender
        refl_send_sidlist : list
            The SID list used by the reflector
        """

        # Get the gRPC channel of the sender
        send_channel = self.__get_grpc_session(sender)
        # Get the gRPC channel of the reflector
        refl_channel = self.__get_grpc_session(reflector)
        # Retrieve the results of the experiment
        print("\n************** Get Measurement Data **************\n")
        # Retrieve the results from the sender
        sender_res = grpc_client.retriveExperimentResultsSender(
            channel=send_channel,
            sidlist=send_refl_sidlist
        )
        # Pretty print status code
        self.__print_status_message(
            status_code=sender_res.status,
            success_msg='Received Data Sender',
            failure_msg='Error in retriveExperimentResultsSender()'
        )
        # Collect the results
        res = None
        if sender_res.status == srv6pmCommons_pb2.STATUS_SUCCESS:
            res = list()
            for data in sender_res.measurement_data:
                res.append({
                    'measure_id': data.meas_id,
                    'interval': data.interval,
                    'timestamp': data.timestamp,
                    'color': data.fwColor,
                    'sender_tx_counter': data.ssTxCounter,
                    'sender_rx_counter': data.ssRxCounter,
                    'reflector_tx_counter': data.rfTxCounter,
                    'reflector_rx_counter': data.rfRxCounter,
                })
        # Return the results
        return res

    def __stop_measurement(self, sender, reflector,
                         send_refl_sidlist, refl_send_sidlist):
        """Stop a measurement process on reflector and sender.

        Parameters
        ----------
        sender : str
            The IP address of the sender node
        reflector : str
            The IP address of the reflector node
        send_refl_sidlist : list
            The SID list used by the sender
        refl_send_sidlist : list
            The SID list used by the reflector
        """

        # Get the gRPC channel of the sender
        send_channel = self.__get_grpc_session(sender)
        # Get the gRPC channel of the reflector
        refl_channel = self.__get_grpc_session(reflector)
        print("\n************** Stop Measurement **************\n")
        # Stop the experiment on the sender
        sender_res = grpc_client.stopExperimentSender(
            channel=send_channel,
            sidlist=send_refl_sidlist
        )
        # Pretty print status code
        self.__print_status_message(
            status_code=sender_res.status,
            success_msg='Stopped Measure Sender',
            failure_msg='Error in stopExperimentSender()'
        )
        # Check for errors
        if sender_res.status != srv6pmCommons_pb2.STATUS_SUCCESS:
            return sender_res.status
        # Stop the experiment on the reflector
        refl_res = grpc_client.stopExperimentReflector(
            channel=refl_channel,
            sidlist=refl_send_sidlist
        )
        # Pretty print status code
        self.__print_status_message(
            status_code=refl_res.status,
            success_msg='Stopped Measure Reflector',
            failure_msg='Error in stopExperimentReflector()'
        )
        # Check for errors
        if refl_res.status != srv6pmCommons_pb2.STATUS_SUCCESS:
            return refl_res.status
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

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
                         send_refl_localseg=None, refl_send_localseg=None,
                         force=False):
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
        send_refl_localseg : str, optional
            The local segment associated to the End.DT6 function on the sender
            (default is None).
            If the argument 'send_localseg' isn't passed in, the seg6local
            End.DT6 route is not created.
        refl_send_localseg : str, optional
            The local segment associated to the End.DT6 function on the
            reflector (default is None).
            If the argument 'send_localseg' isn't passed in, the seg6local
            End.DT6 route is not created.
        force : bool, optional
            If set, force the controller to start an experiment if a
            SRv6 path for the destination already exists. The old SRv6 path
            is replaced with the new one (default is False).
        """

        # Get a new measure ID, if it isn't passed in as argument
        if measure_id is None:
            self.measure_id += 1
            measure_id = self.measure_id
        # If the force flag is set and SRv6 path already exists, remove
        # the old path before creating the new one
        res = self.__destroy_srv6_path(
            node_l=sender,
            node_r=reflector,
            dest_lr=send_refl_dest,
            dest_rl=refl_send_dest,
            localseg_lr=send_refl_localseg,
            localseg_rl=refl_send_localseg,
            ignore_errors=True
        )
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Create a bidirectional SRv6 tunnel between the sender and the
        # reflector
        res = self.__create_srv6_path(
            node_l=sender,
            node_r=reflector,
            dest_lr=send_refl_dest,
            dest_rl=refl_send_dest,
            localseg_lr=send_refl_localseg,
            localseg_rl=refl_send_localseg,
            sidlist_lr=send_refl_sidlist,
            sidlist_rl=refl_send_sidlist
        )
        # Check for errors
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Start measurement process
        res = self.__start_measurement(
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
        # Check for errors
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    def get_experiment_results(self, sender, reflector,
                               send_refl_sidlist, refl_send_sidlist):
        """Get the results of an experiment.

        Parameters
        ----------
        sender : str
            The IP address of the sender node
        reflector : str
            The IP address of the reflector node
        send_refl_sidlist : list
            The SID list to be used by the sender
        refl_send_sidlist : list
            The SID list to be used by the reflector
        """

        # Get the results
        return self.__get_measurement_results(
            sender=sender,
            reflector=reflector,
            send_refl_sidlist=send_refl_sidlist,
            refl_send_sidlist=refl_send_sidlist
        )

    def stop_experiment(self, sender, reflector, send_refl_dest,
                        refl_send_dest, send_refl_sidlist, refl_send_sidlist,
                        send_refl_localseg=None, refl_send_localseg=None):
        """Stop a running experiment.

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
            The SID list used by the sender
        refl_send_sidlist : list
            The SID list used by the reflector
        send_refl_localseg : str, optional
            The local segment associated to the End.DT6 function on the sender
            (default is None).
            If the argument 'send_localseg' isn't passed in, the seg6local
            End.DT6 route is not removed.
        refl_send_localseg : str, optional
            The local segment associated to the End.DT6 function on the
            reflector (default is None).
            If the argument 'send_localseg' isn't passed in, the seg6local
            End.DT6 route is not removed.
        """

        # Stop the experiment
        res = self.__stop_measurement(
            sender=sender,
            reflector=reflector,
            send_refl_sidlist=send_refl_sidlist,
            refl_send_sidlist=refl_send_sidlist
        )
        # Check for errors
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Remove the SRv6 path
        res = self.__destroy_srv6_path(
            node_l=sender,
            node_r=reflector,
            dest_lr=send_refl_dest,
            dest_rl=refl_send_dest,
            localseg_lr=send_refl_localseg,
            localseg_rl=refl_send_localseg
        )
        # Check for errors
        if res != srv6pmCommons_pb2.STATUS_SUCCESS:
            return res
        # Success
        return srv6pmCommons_pb2.STATUS_SUCCESS

    class _SRv6PMService(
            srv6pmServiceController_pb2_grpc.SRv6PMControllerServicer):
        """Private class implementing methods exposed by the gRPC server"""

        def __init__(self, controller):
            """
            Parameters
            ----------
            controller : SRv6Controller
                the reference of the SRv6 controller
            """

            # The reference of the SRv6 controller
            self.controller = controller

        def SendMeasurementData(self, request, context):
            """RPC used to send measurement data to the controller"""

            logger.debug('Measurement data received: %s' % request)
            # Extract data from the request
            for data in request.measurement_data:
                measure_id = data.measure_id
                interval = data.interval
                timestamp = data.timestamp
                color = data.color
                sender_tx_counter = data.sender_tx_counter
                sender_rx_counter = data.sender_rx_counter
                reflector_tx_counter = data.reflector_tx_counter
                reflector_rx_counter = data.reflector_rx_counter
                # Publish data on Kafka
            status = srv6pmCommons_pb2.StatusCode.Value('STATUS_SUCCESS')
            return srv6pmServiceController_pb2.SendMeasurementDataResponse(
                status=status)

    def __start_grpc_server(self,
                            grpc_ip=DEFAULT_GRPC_SERVER_IP,
                            grpc_port=DEFAULT_GRPC_SERVER_PORT,
                            secure=DEFAULT_SERVER_SECURE,
                            key=DEFAULT_SERVER_KEY,
                            certificate=DEFAULT_SERVER_CERTIFICATE):
        """Start gRPC on the controller

        Parameters
        ----------
        grpc_ip : str
            the IP address of the gRPC server
        grpc_port : int
            the port of the gRPC server
        secure : bool
            define whether to use SSL or not for the gRPC server
            (default is False)
        certificate : str
            the path of the server certificate required for the SSL
            (default is None)
        key : str
            the path of the server key required for the SSL
            (default is None)
        """

        # Setup gRPC server
        #
        # Create the server and add the handler
        grpc_server = grpc.server(futures.ThreadPoolExecutor())
        srv6pmServiceController_pb2_grpc \
            .add_SRv6PMControllerServicer_to_server(self._SRv6PMService(self),
                                                    grpc_server)
        # If secure mode is enabled, we need to create a secure endpoint
        if secure:
            # Read key and certificate
            with open(key) as f:
                key = f.read()
            with open(certificate) as f:
                certificate = f.read()
            # Create server SSL credentials
            grpc_server_credentials = grpc.ssl_server_credentials(
                ((key, certificate,),)
            )
            # Create a secure endpoint
            grpc_server.add_secure_port(
                '[%s]:%s' % (grpc_ip, grpc_port),
                grpc_server_credentials
            )
        else:
            # Create an insecure endpoint
            grpc_server.add_insecure_port(
                '[%s]:%s' % (grpc_ip, grpc_port)
            )
        # Start the loop for gRPC
        logger.info('Listening gRPC')
        grpc_server.start()
        while True:
            time.sleep(5)


def __parse_arguments():
    """Parse options received from command-line"""

    # Get parser
    parser = ArgumentParser(
        description='SRv6 Controller'
    )
    # Port of the gRPC server
    parser.add_argument(
        '-a', '--grpc-server-ip', dest='grpc_server_ip', action='store',
        default=DEFAULT_GRPC_SERVER_IP, help='IP address of the gRPC server'
    )
    # Port of the gRPC server
    parser.add_argument(
        '-p', '--grpc-server-port', dest='grpc_server_port', action='store',
        default=DEFAULT_GRPC_SERVER_PORT, help='Port of the gRPC server'
    )
    # Port of the gRPC client
    parser.add_argument(
        '-g', '--grpc-client-port', dest='grpc_client_port', action='store',
        default=DEFAULT_GRPC_CLIENT_PORT, help='Port of the gRPC client'
    )
    # Define whether to use SSL or not for the gRPC client
    parser.add_argument(
        '-s', '--client-secure', action='store_true',
        help='Activate secure mode for the gRPC client',
        default=DEFAULT_CLIENT_SECURE
    )
    # SSL certificate of the root CA
    parser.add_argument(
        '-c', '--client-cert', dest='client_cert', action='store',
        default=DEFAULT_CLIENT_CERTIFICATE, help='Client certificate file'
    )
    # Define whether to use SSL or not for the gRPC server
    parser.add_argument(
        '-a', '--server-secure', action='store_true',
        help='Activate secure mode for the gRPC server',
        default=DEFAULT_SERVER_SECURE
    )
    # SSL certificate of the gRPC server
    parser.add_argument(
        '-b', '--server-cert', dest='client_cert', action='store',
        default=DEFAULT_SERVER_CERTIFICATE, help='Server certificate file'
    )
    # SSL key of the gRPC server
    parser.add_argument(
        '-c', '--server-key', dest='client_cert', action='store',
        default=DEFAULT_SERVER_KEY, help='Server key file'
    )
    # Define whether to enable debug mode or not
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
    args = __parse_arguments()
    # gRPC server IP address
    grpc_server_ip = args.grpc_server_ip
    # gRPC server port
    grpc_server_port = args.grpc_server_port
    # gRPC client port
    # We assume that the same port is used
    # by all the gRPC server
    grpc_client_port = args.grpc_client_port
    # Setup properly the secure mode for the gRPC client
    client_secure = args.client_secure
    # SSL certificate of the root CA required for gRPC secure mode
    client_certificate = args.client_cert
    # Setup properly the secure mode for the gRPC server
    server_secure = args.server_secure
    # SSL certificate of the gRPC server
    server_certificate = args.server_cert
    # SSL key of the gRPC server
    server_key = args.server_key
    # Setup properly the logger
    if args.debug:
        logger.setLevel(level=logging.DEBUG)
    else:
        logger.setLevel(level=logging.INFO)
    # Debug settings
    server_debug = logger.getEffectiveLevel() == logging.DEBUG
    logger.info('SERVER_DEBUG:' + str(server_debug))
    # Test controller
    controller = SRv6Controller(
        grpc_server_ip=grpc_server_ip,
        grpc_server_port=grpc_server_port,
        grpc_client_port=grpc_client_port,
        grpc_client_secure=client_secure,
        grpc_client_certificate=client_certificate,
        grpc_server_secure=server_secure,
        grpc_server_certificate=server_certificate,
        grpc_server_key=server_key,
        debug=args.debug,
    )
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
