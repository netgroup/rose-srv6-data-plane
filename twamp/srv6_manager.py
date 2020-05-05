#!/usr/bin/python


from __future__ import absolute_import, division, print_function

# General imports
from argparse import ArgumentParser
import logging
import time
import grpc
from concurrent import futures
from pyroute2 import IPRoute
from socket import AF_INET6
# pyroute2 dependencies
from pyroute2.netlink.exceptions import NetlinkError
from pyroute2.netlink.rtnl.ifinfmsg import IFF_LOOPBACK

# SRv6PM dependencies
import srv6_manager_pb2
import srv6_manager_pb2_grpc
import srv6pmCommons_pb2


# Global variables definition
#
#
# Netlink error codes
NETLINK_ERROR_NO_SUCH_PROCESS = 3
NETLINK_ERROR_FILE_EXISTS = 17
NETLINK_ERROR_NO_SUCH_DEVICE = 19
NETLINK_ERROR_OPERATION_NOT_SUPPORTED = 95
# Logger reference
logger = logging.getLogger(__name__)
#
# Default parameters for SRv6 controller
#
# Server ip and port
DEFAULT_GRPC_IP = '::'
DEFAULT_GRPC_PORT = 12345
# Debug option
SERVER_DEBUG = False
# Secure option
DEFAULT_SECURE = False
# Server certificate
DEFAULT_CERTIFICATE = 'cert_server.pem'
# Server key
DEFAULT_KEY = 'key_server.pem'


class SRv6Manager(srv6_manager_pb2_grpc.SRv6ManagerServicer):
    '''gRPC request handler'''

    def __init__(self):
        # Setup ip route
        self.ip_route = IPRoute()
        # Non-loopback interfaces
        self.non_loopback_interfaces = list()
        # Loopback interfaces
        self.loopback_interfaces = list()
        # Mapping interface name to interface index
        self.interface_to_idx = dict()
        # Resolve the interfaces
        for link in self.ip_route.get_links():
            # Check the IFF_LOOPBACK flag of the interfaces
            # and make separation between loopback interfaces and
            # non-loopback interfaces
            if not link.get('flags') & IFF_LOOPBACK == 0:
                self.loopback_interfaces.append(
                    link.get_attr('IFLA_IFNAME'))
            else:
                self.non_loopback_interfaces.append(link.get_attr('IFLA_IFNAME'))        
        # Build mapping interface to index
        interfaces = self.loopback_interfaces + self.non_loopback_interfaces
        # Iterate on the interfaces
        for interface in interfaces:
            # Add interface index
            self.interface_to_idx[interface] = \
                self.ip_route.link_lookup(ifname=interface)[0]

    def parse_netlink_error(self, e):
        if e.code == NETLINK_ERROR_FILE_EXISTS:
            logger.warning('Netlink error: File exists')
            return srv6pmCommons_pb2.STATUS_FILE_EXISTS
        elif e.code == NETLINK_ERROR_NO_SUCH_PROCESS:
            logger.warning('Netlink error: No such process')
            return srv6pmCommons_pb2.STATUS_NO_SUCH_PROCESS
        elif e.code == NETLINK_ERROR_NO_SUCH_DEVICE:
            logger.warning('Netlink error: No such device')
            return srv6pmCommons_pb2.STATUS_NO_SUCH_DEVICE
        elif e.code == NETLINK_ERROR_OPERATION_NOT_SUPPORTED:
            logger.warning('Netlink error: Operation not supported')
            return srv6pmCommons_pb2.STATUS_OPERATION_NOT_SUPPORTED
        else:
            logger.warning('Generic internal error: %s' % e)
            srv6pmCommons_pb2.STATUS_INTERNAL_ERROR

    def HandleSRv6PathRequest(self, op, request, context):
        logger.debug('config received:\n%s', request)
        # Perform operation
        try:
            if op == 'add' or 'del':
                # Let's push the routes
                for path in request.paths:
                    # Rebuild segments
                    segments = []
                    for srv6_segment in path.sr_path:
                        segments.append(srv6_segment.segment)
                    table = path.table
                    if path.table == -1:
                        table = None
                    if segments == []:
                        segments = ['::']
                    if path.device != '':
                        oif = self.interface_to_idx[path.device]
                    else:
                        oif = self.interface_to_idx[self.non_loopback_interfaces[0]]
                    self.ip_route.route(op, dst=path.destination, oif=oif,
                                        table=table,
                                        encap={'type': 'seg6',
                                               'mode': path.encapmode,
                                               'segs': segments})
            else:
                # Operation unknown: this is a bug
                logger.error('Unrecognized operation: %s' % op)
                exit(-1)
            # and create the response
            logger.debug('Send response: OK')
            return srv6_manager_pb2.SRv6ManagerReply(
                status=srv6pmCommons_pb2.STATUS_SUCCESS)
        except NetlinkError as e:
            return srv6_manager_pb2.SRv6ManagerReply(
                status=self.parse_netlink_error(e))

    def HandleSRv6BehaviorRequest(self, op, request, context):
        logger.debug('config received:\n%s', request)
        # Let's process the request
        try:
            for behavior in request.behaviors:
                # Extract params from request
                segment = behavior.segment
                action = behavior.action
                nexthop = behavior.nexthop
                table = behavior.table
                interface = behavior.interface
                device = behavior.device
                localsid_table = behavior.localsid_table
                # Check optional params
                nexthop = nexthop if nexthop != '' else None
                table = table if table != -1 else None
                interface = interface if interface != '' else None
                device = device if device != '' else self.non_loopback_interfaces[0]
                localsid_table = localsid_table if localsid_table != -1 else None
                # Perform operation
                if op == 'del':
                    # Delete a route
                    self.ip_route.route(op, family=AF_INET6, dst=segment,
                                        table=localsid_table)
                elif op == 'add':
                    # Add a new route
                    if action == 'End':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End'})
                    elif action == 'End.X':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.X',
                                                   'nh6': nexthop})
                    elif action == 'End.T':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.T',
                                                   'table': table})
                    elif action == 'End.DX2':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.DX2',
                                                   'oif': interface})
                    elif action == 'End.DX6':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.DX6',
                                                   'nh6': nexthop})
                    elif action == 'End.DX4':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.DX4',
                                                   'nh4': nexthop})
                    elif action == 'End.DT6':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.DT6',
                                                   'table': table})
                    elif action == 'End.DT4':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.DT4',
                                                   'table': table})
                    elif action == 'End.DT46':
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.DT46',
                                                   'table': table})
                    elif action == 'End.B6':
                        # Rebuild segments
                        segments = []
                        for srv6_segment in behavior.segs:
                            segments.append(srv6_segment.segment)
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.B6',
                                                   'srh': {'segs': segments}})
                    elif action == 'End.B6.Encaps':
                        # Rebuild segments
                        segments = []
                        for srv6_segment in behavior.segs:
                            segments.append(srv6_segment.segment)
                        self.ip_route.route(op, family=AF_INET6, dst=segment,
                                            oif=self.interface_to_idx[device],
                                            table=localsid_table,
                                            encap={'type': 'seg6local',
                                                   'action': 'End.B6.Encaps',
                                                   'srh': {'segs': segments}})
                    else:
                        logger.debug('Error: Unrecognized action')
                        return srv6_manager_pb2.SRv6ManagerReply(
                            status=srv6pmCommons_pb2.STATUS_INVALID_ACTION)
                else:
                    # Operation unknown: this is a bug
                    logger.error('Unrecognized operation: %s' % op)
                    exit(-1)
            # and create the response
            logger.debug('Send response: OK')
            return srv6_manager_pb2.SRv6ManagerReply(
                status=srv6pmCommons_pb2.STATUS_SUCCESS)
        except NetlinkError as e:
            return srv6_manager_pb2.SRv6ManagerReply(
                status=self.parse_netlink_error(e))

    def HandleInterfaceRequest(self, op, request, context):
        logger.debug('config received:\n%s', request)
        # Let's process the request
        try:
            if op == 'get':
                # Handle get operation
                # Get the interfaces
                interfaces = list()
                for link in self.ip_route.get_links():
                    if (link.get_attr('IFLA_LINKINFO') and
                        link.get_attr('IFLA_LINKINFO')
                            .get_attr('IFLA_INFO_KIND') == 'vrf'):
                        # Skip the VRFs
                        continue
                    # Get the name of the interface
                    ifname = link.get_attr('IFLA_IFNAME')
                    # Save the interface
                    interfaces.append(ifname)
                # Create the response
                response = srv6_manager_pb2.SRv6ManagerReply(
                    status=srv6pmCommons_pb2.STATUS_SUCCESS)
                for interface in interfaces:
                    interface = response.interfaces.add()
                    interface.name = ifname
                logger.debug('Send response:\n%s', response)
                return response
            else:
                # Operation unknown: this is a bug
                logger.error('Unrecognized operation: %s' % op)
        except NetlinkError as e:
            return srv6_manager_pb2.SRv6ManagerReply(
                status=self.parse_netlink_error(e))

    def Execute(self, op, request, context):
        entity_type = request.entity_type
        # Handle operation
        # The operation to be executed depends on
        # the entity carried by the request message
        if entity_type == srv6_manager_pb2.SRv6PathEntity:
            request = request.srv6_path_request
            return self.HandleSRv6PathRequest(op, request, context)
        elif entity_type == srv6_manager_pb2.SRv6BehaviorEntity:
            request = request.srv6_behavior_request
            return (self.HandleSRv6BehaviorRequest(op, request,
                                                   context))
        elif entity_type == srv6_manager_pb2.Interface:
            request = request.interface_request
            return self.HandleInterfaceRequest(op, request, context)
        else:
            return (srv6_manager_pb2.SRv6ManagerReply(
                status=srv6pmCommons_pb2.STATUS_INVALID_GRPC_REQUEST))

    def Create(self, request, context):
        # Handle Create operation
        return self.Execute('add', request, context)

    def Get(self, request, context):
        # Handle Create operation
        return self.Execute('get', request, context)

    def Update(self, request, context):
        # Handle Remove operation
        return self.Execute('change', request, context)

    def Remove(self, request, context):
        # Handle Remove operation
        return self.Execute('del', request, context)


# Start gRPC server
def start_server(grpc_ip=DEFAULT_GRPC_IP,
                 grpc_port=DEFAULT_GRPC_PORT,
                 secure=DEFAULT_SECURE,
                 certificate=DEFAULT_CERTIFICATE,
                 key=DEFAULT_KEY):
    # Create the server and add the handlers
    grpc_server = grpc.server(futures.ThreadPoolExecutor())
    (srv6_manager_pb2_grpc
        .add_SRv6ManagerServicer_to_server(
            SRv6Manager(), grpc_server)
     )
    # If secure we need to create a secure endpoint
    if secure:
        # Read key and certificate
        with open(key, 'rb') as f:
            key = f.read()
        with open(certificate, 'rb') as f:
            certificate = f.read()
        # Create server ssl credentials
        grpc_server_credentials = (grpc
                                   .ssl_server_credentials(((key,
                                                             certificate),)))
        # Create a secure endpoint
        grpc_server.add_secure_port('[%s]:%s' % (grpc_ip, grpc_port),
                                    grpc_server_credentials)
    else:
        # Create an insecure endpoint
        grpc_server.add_insecure_port('[%s]:%s' % (grpc_ip, grpc_port))
    # Start the loop for gRPC
    logger.info('*** Listening gRPC')
    grpc_server.start()
    while True:
        time.sleep(5)


# Parse options
def parse_arguments():
    # Get parser
    parser = ArgumentParser(
        description='gRPC Southbound APIs for SRv6 Controller'
    )
    parser.add_argument(
        '-g', '--grpc-ip', dest='grpc_ip', action='store',
        default=DEFAULT_GRPC_IP, help='IP of the gRPC server'
    )
    parser.add_argument(
        '-r', '--grpc-port', dest='grpc_port', action='store',
        default=DEFAULT_GRPC_PORT, help='Port of the gRPC server'
    )
    parser.add_argument(
        '-s', '--secure', action='store_true', help='Activate secure mode'
    )
    parser.add_argument(
        '-c', '--server-cert', dest='server_cert', action='store',
        default=DEFAULT_CERTIFICATE, help='Server certificate file'
    )
    parser.add_argument(
        '-k', '--server-key', dest='server_key',
        action='store', default=DEFAULT_KEY, help='Server key file'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true', help='Activate debug logs'
    )
    # Parse input parameters
    args = parser.parse_args()
    # Return the arguments
    return args


if __name__ == '__main__':
    args = parse_arguments()
    # Setup properly the secure mode
    secure = args.secure
    # gRPC server IP
    grpc_ip = args.grpc_ip
    # gRPC server port
    grpc_port = args.grpc_port
    # Server certificate
    certificate = args.server_cert
    # Server key
    key = args.server_key
    # Setup properly the logger
    if args.debug:
        logger.setLevel(level=logging.DEBUG)
    else:
        logger.setLevel(level=logging.INFO)
    # Debug settings
    server_debug = logger.getEffectiveLevel() == logging.DEBUG
    logging.info('SERVER_DEBUG:' + str(server_debug))
    # Start the server
    start_server(grpc_ip, grpc_port, secure, certificate, key)
