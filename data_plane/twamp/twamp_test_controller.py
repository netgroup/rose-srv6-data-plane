from concurrent import futures
import grpc
import logging

import time


import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmService_pb2_grpc
import srv6pmService_pb2
import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc


def startExperimentSender(stub):
    request = srv6pmSender_pb2.StartExperimentSenderRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.startExperimentSender(request=request)

def startExperimentReflector(stub):
    request = srv6pmReflector_pb2.StartExperimentReflectorRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.startExperimentReflector(request=request)


def stopExperimentSender(stub):
    request = srv6pmCommons_pb2.StopExperimentRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.stopExperimentSender(request=request)

def stopExperimentReflector(stub):
    request = srv6pmCommons_pb2.StopExperimentRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.stopExperimentReflector(request=request)

def retriveExperimentResults(stub):
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.retriveExperimentResults(request=request)


def test_deamon():
    with grpc.insecure_channel('10.1.1.1:50050') as channel1, \
            grpc.insecure_channel('10.1.1.2:50050') as channel2:
        sender = srv6pmService_pb2_grpc.SRv6PMStub(channel1)
        reflector = srv6pmService_pb2_grpc.SRv6PMStub(channel2)

        print("\n-------------- startMeas --------------\n")
        sender_res = startExperimentSender(sender)
        if sender_res is not None and sender_res.status == 1:
            print("Started Measure Sender RES:"+str(sender_res.status))
        else:
            print("ERROR startExperimentSender  RES:"+sender_res)

        refl_res = startExperimentReflector(reflector)
        if refl_res is not None and refl_res.status == 1:
            print("Started Measure Reflector RES:"+str(refl_res.status))
        else:
            print("ERROR startExperimentReflector  RES:"+refl_res)

        for i in range(3):
            time.sleep(5)
            print("\n-------------- get Meas Data --------------\n")
            sender_res = retriveExperimentResults(sender)
            if sender_res is not None:
                print("Received Data Sender RES:"+str(sender_res.status))
            else:
                print("ERROR retriveExperimentResultsSender RES:"+sender_res)

        
        time.sleep(2)
        print("\n-------------- stop Meas --------------\n")
        sender_res = stopExperimentSender(sender)
        if sender_res is not None and sender_res.status == 1:
            print("Stopped Measure RES:"+str(sender_res.status))
        else:
            print("ERROR startExperimentSender RES:"+sender_res)

        refl_res = stopExperimentReflector(reflector)
        if refl_res is not None and refl_res.status == 1:
            print("Stopped Measure RES:"+str(refl_res.status))
        else:
            print("ERROR startExperimentSender RES:"+refl_res)


if __name__ == '__main__':
    logging.basicConfig()
    test_deamon()
