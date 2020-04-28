#!/usr/bin/python

from __future__ import absolute_import, division, print_function

# General imports
from six import text_type
import grpc
import json
import sys
import os
import logging
from socket import AF_INET, AF_INET6
from threading import Thread

from ipaddress import IPv4Interface, IPv6Interface
from ipaddress import AddressValueError
from socket import AF_INET, AF_INET6

# SRv6 PM dependencies
import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc
import srv6pmCommons_pb2
import srv6pmCommons_pb2_grpc
import srv6pmService_pb2
import srv6pmService_pb2_grpc
import srv6_manager_pb2
import srv6_manager_pb2_grpc


# Global variables definition
#
#
# Logger reference
logger = logging.getLogger(__name__)

 
# Utiliy function to check if the IP
# is a valid IPv6 address
def validate_ipv6_address(ip):
   if ip is None:
       return False
   try:
       IPv6Interface(ip)
       return True
   except AddressValueError:
       return False
 
 
# Utiliy function to check if the IP
# is a valid IPv4 address
def validate_ipv4_address(ip):
   if ip is None:
       return False
   try:
       IPv4Interface(ip)
       return True
   except AddressValueError:
       return False
 
# Utiliy function to get the IP address family
def getAddressFamily(ip):
   if validate_ipv6_address(ip):
       # IPv6 address
       return AF_INET6
   elif validate_ipv4_address(ip):
       # IPv4 address
       return AF_INET
   else:
       # Invalid address
       return None

# Build a grpc stub
def get_grpc_session(server_ip, server_port,
                     secure=False, certificate=None):
    addr_family = getAddressFamily(server_ip)
    if addr_family == AF_INET6:
        server_ip = "ipv6:[%s]:%s" % (server_ip, server_port)
    elif addr_family == AF_INET:
        server_ip = "ipv4:%s:%s" % (server_ip, server_port)
    else:
        print('Invalid address: %s' % server_ip)
        return
    # If secure we need to establish a channel with the secure endpoint
    if secure:
        if certificate is None:
            logger.fatal('Certificate required for gRPC secure mode')
            exit(-1)
        # Open the certificate file
        with open(certificate, 'rb') as f:
            certificate = f.read()
        # Then create the SSL credentials and establish the channel
        grpc_client_credentials = grpc.ssl_channel_credentials(certificate)
        channel = grpc.secure_channel(server_ip, grpc_client_credentials)
    else:
        channel = grpc.insecure_channel(server_ip)
    # Return the channel
    return channel


# Parser for gRPC errors
def parse_grpc_error(e):
    status_code = e.code()
    details = e.details()
    logger.error('gRPC client reported an error: %s, %s'
                 % (status_code, details))
    if grpc.StatusCode.UNAVAILABLE == status_code:
        code = srv6pmCommons_pb2.STATUS_GRPC_SERVICE_UNAVAILABLE
    elif grpc.StatusCode.UNAUTHENTICATED == status_code:
        code = srv6pmCommons_pb2.STATUS_GRPC_UNAUTHORIZED
    else:
        code = srv6pmCommons_pb2.STATUS_INTERNAL_ERROR
    # Return an error message
    return code


def startExperimentSender(channel, in_sidlist, out_sidlist,
                          in_interfaces, out_interfaces,
                          measurement_protocol, dst_udp_port,
                          measurement_type, authentication_mode, authentication_key,
                          timestamp_format, delay_measurement_mode,
                          padding_mbz, loss_measurement_mode, interval_duration,
                          delay_margin, number_of_color):
    # Get the reference of the stub
    stub = srv6pmService_pb2_grpc.SRv6PMStub(channel)
    # Create the request
    request = srv6pmSender_pb2.StartExperimentSenderRequest()
    # Set the SID list
    request.sdlist = '/'.join(out_sidlist)
    #
    # Set the sender options
    #
    # Set the measureemnt protocol
    request.sender_options.measurement_protocol = \
        srv6pmCommons_pb2.MeasurementProtocol.Value(measurement_protocol)
    # Set the destination UDP port
    request.sender_options.dst_udp_port = int(dst_udp_port)
    # Set the authentication mode
    request.sender_options.authentication_mode = \
        srv6pmCommons_pb2.AuthenticationMode.Value(authentication_mode)
    # Set the authentication key
    request.sender_options.authentication_key = str(authentication_key)
    # Set the measurement type
    request.sender_options.measurement_type = \
        srv6pmCommons_pb2.MeasurementType.Value(measurement_type)
    # Set the timestamp format
    request.sender_options.timestamp_format = \
        srv6pmCommons_pb2.TimestampFormat.Value(timestamp_format)
    # Set the measurement delay mode
    request.sender_options.measurement_delay_mode = \
        srv6pmCommons_pb2.MeasurementDelayMode.Value(delay_measurement_mode)
    # Set the padding
    request.sender_options.padding_mbz = int(padding_mbz)
    # Set the measurement loss mode
    request.sender_options.measurement_loss_mode = \
        srv6pmCommons_pb2.MeasurementLossMode.Value(loss_measurement_mode)
    #
    # Set the color options
    #
    # Set the interval duration
    request.color_options.interval_duration = int(interval_duration)
    # Set the delay margin
    request.color_options.delay_margin = int(delay_margin)
    # Set the number of color
    request.color_options.numbers_of_color = int(number_of_color)
    #
    # Start the experiment on the sender and return the response
    return stub.startExperimentSender(request=request)


def stopExperimentSender(channel, sidlist):
    # Get the reference of the stub
    stub = srv6pmService_pb2_grpc.SRv6PMStub(channel)
    # Create the request message
    request = srv6pmCommons_pb2.StopExperimentRequest()
    # Set the SID list
    request.sdlist = '/'.join(sidlist)
    # Stop the experiment on the sender and return the response
    return stub.stopExperimentSender(request=request)


def retriveExperimentResultsSender(channel, sidlist):
    # Get the reference of the stub
    stub = srv6pmService_pb2_grpc.SRv6PMStub(channel)
    # Create the request message
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    # Set the SID list
    request.sdlist = '/'.join(sidlist)
    # Retrieve the experiment results from the sender and return them
    return stub.retriveExperimentResults(request=request)


def startExperimentReflector(channel, in_sidlist, out_sidlist,
                             in_interfaces, out_interfaces,
                             measurement_protocol, dst_udp_port,
                             measurement_type, authentication_mode, authentication_key,
                             loss_measurement_mode, interval_duration,
                             delay_margin, number_of_color):
    # Get the reference of the stub
    stub = srv6pmService_pb2_grpc.SRv6PMStub(channel)
    # Create the request message
    request = srv6pmReflector_pb2.StartExperimentReflectorRequest()
    # Set the SID list
    request.sdlist = '/'.join(out_sidlist)
    #
    # Set the reflector options
    #
    # Set the measureemnt protocol
    request.reflector_options.measurement_protocol = \
        srv6pmCommons_pb2.MeasurementProtocol.Value(measurement_protocol)
    # Set the destination UDP port
    request.reflector_options.dst_udp_port = int(dst_udp_port)
    # Set the authentication mode
    request.reflector_options.authentication_mode = \
        srv6pmCommons_pb2.AuthenticationMode.Value(authentication_mode)
    # Set the authentication key
    request.reflector_options.authentication_key = str(authentication_key)
    # Set the measurement type
    request.reflector_options.measurement_type = \
        srv6pmCommons_pb2.MeasurementType.Value(measurement_type)
    # Set the measurement loss mode
    request.reflector_options.measurement_loss_mode = \
        srv6pmCommons_pb2.MeasurementLossMode.Value(loss_measurement_mode)
    #
    # Set the color options
    #
    # Set the interval duration
    request.color_options.interval_duration = int(interval_duration)
    # Set the delay margin
    request.color_options.delay_margin = int(delay_margin)
    # Set the number of color
    request.color_options.numbers_of_color = int(number_of_color)
    # Start the experiment on the reflector and return the response
    return stub.startExperimentReflector(request=request)


def stopExperimentReflector(channel, sidlist):
    # Get the reference of the stub
    stub = srv6pmService_pb2_grpc.SRv6PMStub(channel)
    # Create the request message
    request = srv6pmCommons_pb2.StopExperimentRequest()
    # Set the SID list
    request.sdlist = '/'.join(sidlist)
    # Stop the experiment on the reflector and return the response
    return stub.stopExperimentReflector(request=request)


def retriveExperimentResultsReflector(channel, sidlist):
    # Get the reference of the stub
    stub = srv6pmService_pb2_grpc.SRv6PMStub(channel)
    # Create the request message
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    # Set the SID list
    request.sdlist = '/'.join(sidlist)
    # Retrieve the experiment results fromt he reflector and return them
    return stub.retriveExperimentResults(request=request)


def add_srv6_path(channel, destination, segments,
                           device='', encapmode="encap", table=-1):
    # Create request message
    request = srv6_manager_pb2.SRv6ManagerRequest()
    # Set the type of the carried entity
    request.entity_type = srv6_manager_pb2.SRv6PathEntity
    # Create a new SRv6 path request
    path_request = request.srv6_path_request
    # Create a new path
    path = path_request.paths.add()
    # Set destination
    path.destination = text_type(destination)
    # Set device
    # If the device is not specified (i.e. empty string),
    # it will be chosen by the gRPC server
    path.device = text_type(device)
    # Set encapmode
    path.encapmode = text_type(encapmode)
    # Set table ID
    # If the table ID is not specified (i.e. table=-1),
    # the main table will be used
    path.table = int(table)
    # Iterate on the segments and build the SID list
    for segment in segments:
        # Append the segment to the SID list
        srv6_segment = path.sr_path.add()
        srv6_segment.segment = text_type(segment)
    try:
        # Get the reference of the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Create the SRv6 paths
        response = stub.Create(request)
        # Get the status code of the gRPC operation
        response = response.status
    except grpc.RpcError as e:
        # An error occurred during the gRPC operation
        # Parse the error and return it
        response = parse_grpc_error(e)
    # Return the response
    return response


def remove_srv6_path(channel, destination, device='', table=-1):
    # Create the request message
    request = srv6_manager_pb2.SRv6ManagerRequest()
    # Set the type of the carried entity
    request.entity_type = srv6_manager_pb2.SRv6PathEntity
    # Create a new SRv6 path request
    path_request = request.srv6_path_request
    # Create a new path
    path = path_request.paths.add()
    # Set destination
    path.destination = text_type(destination)
    # Set device
    # If the device is not specified (i.e. empty string),
    # it will be chosen by the gRPC server
    path.device = text_type(device)
    # Set table
    # If the table ID is not specified (i.e. table=-1),
    # the main table will be used
    path.table = int(table)
    try:
        # Get the reference of the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Remove the SRv6 paths
        response = stub.Remove(request)
        # Get the status code of the gRPC operation
        response = response.status
    except grpc.RpcError as e:
        # An error occurred during the gRPC operation
        # Parse the error and return it
        response = parse_grpc_error(e)
    # Return the response
    return response


def add_srv6_behavior(channel, segment, action, device='',
                      localsid_table=-1, nexthop="",
                      table=-1, interface="", segments=[]):
    # Create the request message
    request = srv6_manager_pb2.SRv6ManagerRequest()
    # Set the type of the carried entity
    request.entity_type = srv6_manager_pb2.SRv6BehaviorEntity
    # Create a new SRv6 behavior request
    behavior_request = request.srv6_behavior_request
    # Create a new SRv6 behavior
    behavior = behavior_request.behaviors.add()
    # Set local segment for the seg6local route
    behavior.segment = text_type(segment)
    # Set the device
    # If the device is not specified (i.e. empty string),
    # it will be chosen by the gRPC server
    behavior.device = text_type(device)
    # Set the localsid table where the seg6local must be inserted
    # If the table ID is not specified (i.e. localsid_table=-1),
    # the main table will be used
    behavior.localsid_table = int(localsid_table)
    # Set the action for the seg6local route
    behavior.action = text_type(action)
    # Set the nexthop for the L3 cross-connect actions
    # (e.g. End.DX4, End.DX6)
    behavior.nexthop = text_type(nexthop)
    # Set the table for the "decap and table lookup" actions
    # (e.g. End.DT4, End.DT6)
    behavior.table = int(table)
    # Set the inteface for the L2 cross-connect actions
    # (e.g. End.DX2)
    behavior.interface = text_type(interface)
    # Set the segments for the binding SID actions
    # (e.g. End.B6, End.B6.Encaps)
    for segment in segments:
        # Create a new segment
        srv6_segment = behavior.segs.add()
        srv6_segment.segment = text_type(segment)
    try:
        # Get the reference of the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Create the SRv6 behavior
        response = stub.Create(request)
        # Get the status code of the gRPC operation
        response = response.status
    except grpc.RpcError as e:
        # An error occurred during the gRPC operation
        # Parse the error and return it
        response = parse_grpc_error(e)
    # Return the response
    return response


def remove_srv6_behavior(channel, segment, localsid_table=-1, device=""):
    # Create the request message
    request = srv6_manager_pb2.SRv6ManagerRequest()
    # Set the type of the carried entity
    request.entity_type = srv6_manager_pb2.SRv6BehaviorEntity
    # Create a new SRv6 behavior request
    behavior_request = request.srv6_behavior_request
    # Create a new SRv6 behavior
    behavior = behavior_request.behaviors.add()
    # Set local segment for the seg6local route
    behavior.segment = text_type(segment)
    # Set the device
    # If the device is not specified (i.e. empty string),
    # it will be chosen by the gRPC server
    behavior.device = text_type(device)
    # Set the localsid table where the seg6local must be inserted
    # If the table ID is not specified (i.e. localsid_table=-1),
    # the main table will be used
    behavior.localsid_table = int(localsid_table)
    try:
        # Get the reference of the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Remove the SRv6 behavior
        response = stub.Remove(request)
        # Get the status code of the gRPC operation
        response = response.status
    except grpc.RpcError as e:
        # An error occurred during the gRPC operation
        # Parse the error and return it
        response = parse_grpc_error(e)
    # Return the response
    return response


def get_interfaces(channel):
    # Create the request message
    request = srv6_manager_pb2.SRv6ManagerRequest()
    # Set the type of the carried entity
    request.entity_type = srv6_manager_pb2.InterfaceEntity
    try:
        # Get the reference of the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Get interfaces
        response = stub.Get(request)
        # Get the status code of the gRPC operation
        response = response.status
    except grpc.RpcError as e:
        # An error occurred during the gRPC operation
        # Parse the error and return it
        response = parse_grpc_error(e)
    # Return the response
    return response


# Test gRPC client APIs
if __name__ == "__main__":
    with get_grpc_session('fcff:1::1') as channel:
        # Get the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Create a seg6 route
        res = create_seg6_route(
            stub=stub,
            destination='fd00:0:83::/64',
            segments=['fcff:4::1', 'fcff:8::100']
        )
        # Add "Decap and Specific Table Lookup" function
        res = create_seg6local_route(
            stub=stub,
            segment='fcff:8::100',
            action='End.DT6',
            table=254
        )
    with get_grpc_session('fcff:8::1') as channel:
        # Get the stub
        stub = srv6_manager_pb2_grpc.SRv6ManagerStub(channel)
        # Create a seg6 route
        res = create_seg6_route(
            stub=stub,
            destination='fd00:0:11::/64',
            segments=['fcff:4::1', 'fcff:1::100']
        )
        # Add "Decap and Specific Table Lookup" function
        res = create_seg6local_route(
            stub=stub,
            segment='fcff:1::100',
            action='End.DT6',
            table=254
        )
