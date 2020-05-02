from concurrent import futures
import grpc
import logging
import sys
import os
import time
from datetime import datetime, timedelta
import pprint

import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc
import srv6pmCommons_pb2
import srv6pmCommons_pb2_grpc
import srv6pmService_pb2_grpc
import srv6pmService_pb2

def startExperimentSender(stub):
    request = srv6pmSender_pb2.StartExperimentSenderRequest()
    request.sdlist = "fcff:3::1/fcff:4::1/fcff:5::1"
    return stub.startExperimentSender(request=request)


def retriveExperimentResultsSender(stub):
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.retriveExperimentResults(request=request)


def stopExperimentSender(stub):
    request = srv6pmCommons_pb2.StopExperimentRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.stopExperimentSender(request=request)


def startExperimentReflector(stub):
    request = srv6pmSender_pb2.StartExperimentSenderRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.startExperimentReflector(request=request)

def stopExperimentReflector(stub):
    request = srv6pmCommons_pb2.StopExperimentRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.stopExperimentReflector(request=request)

def retriveExperimentResultsReflector(stub):
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.retriveExperimentResults(request=request)

def test_meas():
    with grpc.insecure_channel('10.1.1.1:50052') as channel:
        stub = srv6pmSender_pb2_grpc.SRv6PMSenderStub(channel)

        print("\n-------------- startMeas --------------\n")
        sender_res = startExperimentSender(stub)
        if sender_res!=None and sender_res.status==1:
            print("Started Measure RES:"+str(sender_res.status))
        else: 
            print ("ERROR startExperimentSender  RES:"+sender_res)

        time.sleep(8)
        for i in range(6):
            time.sleep(15)
            print("\n-------------- get Meas Data --------------\n",datetime)
            sender_res = retriveExperimentResultsSender(stub)
            if sender_res!=None :
                print("Received Loss Data RES:"+str(sender_res.status))
            else: 
                print ("ERROR retriveExperimentResultsSender RES:"+sender_res)

        time.sleep(2)
        print("\n-------------- stop Meas --------------\n")
        sender_res = stopExperimentSender(stub)
        if sender_res!=None and sender_res.status==1:
            print("Stopped Measure RES:"+str(sender_res.status))
        else: 
            print ("ERROR startExperimentSender RES:"+sender_res)


def test_meas_2():
    with grpc.insecure_channel('10.1.1.1:50052') as channel1, \
        grpc.insecure_channel('10.1.1.2:50052') as channel2:
        sender = srv6pmService_pb2_grpc.SRv6PMStub(channel1)
        reflector = srv6pmService_pb2_grpc.SRv6PMStub(channel2)

        time.sleep(10)

        print("\n-------------- startMeas --------------\n")
        sender_res = startExperimentSender(sender)
        if sender_res!=None and sender_res.status==1:
            print("Started Measure Sender RES:"+str(sender_res.status))
        else: 
            print ("ERROR startExperimentSender  RES:"+sender_res)

        refl_res = startExperimentReflector(reflector)
        if refl_res!=None and refl_res.status==1:
            print("Started Measure Reflector RES:"+str(refl_res.status))
        else: 
            print ("ERROR startExperimentReflector  RES:"+refl_res)

        time.sleep(8)

        for i in range(6):
            time.sleep(15)
            print("\n-------------- get Meas Data --------------\n")
            sender_res = retriveExperimentResultsSender(sender)
            if sender_res!=None :
                print("Received Data Sender RES:"+str(sender_res.status))
                pprint.pprint(sender_res)
            else: 
                print ("ERROR retriveExperimentResultsSender RES:"+sender_res)
            

        time.sleep(2)
        print("\n-------------- stop Meas --------------\n")
        sender_res = stopExperimentSender(sender)
        if sender_res!=None and sender_res.status==1:
            print("Stopped Measure RES:"+str(sender_res.status))
        else: 
            print ("ERROR startExperimentSender RES:"+sender_res)
        
        refl_res = stopExperimentReflector(reflector)
        if refl_res!=None and refl_res.status==1:
            print("Stopped Measure RES:"+str(refl_res.status))
        else: 
            print ("ERROR startExperimentSender RES:"+refl_res)

if __name__ == '__main__':
    logging.basicConfig()
    test_meas_2()
