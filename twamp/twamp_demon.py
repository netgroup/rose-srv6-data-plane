#!/usr/bin/python

from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time
from scapy.all import *
from scapy.layers.inet import IP,UDP


# FRPC protocol
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmService_pb2_grpc
import srv6pmService_pb2
import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc

from srv6_manager import SRv6Manager
import srv6_manager_pb2
import srv6_manager_pb2_grpc

class TestPacketReceiver(Thread):
    def __init__(self, interface, sender, reflector ):
        Thread.__init__(self) 
        self.interface = interface
        self.SessionSender = sender
        self.SessionReflector = reflector

    def packetRecvCallback(self, packet):
        print("Packets Recv Callback")
        packet[UDP].decode_payload_as(Raw)
        print(packet.show())
		
        ip_layer = packet.getlayer(IP)
        print("[!] New Packet: {src} -> {dst}".format(src=ip_layer.src, dst=ip_layer.dst))
        message = ""
        raw_layer = packet.getlayer(Raw)
        print("[!] TWAMP Payload: {payload} ".format(payload=raw_layer.load))
        self.SessionSender.receveQueryResponse(message)

    def run(self):
        print("TestPacketReceiver Start sniffing...")
        sniff(iface=self.interface, filter="udp and port 862", prn=self.packetRecvCallback)
        print("TestPacketReceiver Stop sniffing")
        # codice netqueue




class SessionSender(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.startedMeas = False
        self.counter = {}
        # self.lock = Thread.Lock()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def startMeas(self, sidList):
        print("CTRL: Start Meas for "+sidList)
        self.counter[sidList] = 0
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("CTRL: Stop Meas for "+sidList)
        self.startedMeas = False

    def doMeasure(self):
        if self.startedMeas:
            print("CTRL: Loss Probe / Color")
            for sl in self.counter:
                self.counter[sl] += 1
        self.scheduler.enter(2, 1, self.doMeasure)

    def getMeas(self, sidList):
        print("CTRL: Get Mead Data for "+sidList)
        return self.counter[sidList]

    def run(self):

        print("SessionSender start")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("SessionSender stop")

    def receveQueryResponse(self, message):
        print("Received response")




class SessionReflector(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.name = "SessionReflector"
        self.startedMeas = False
        self.counter = {}
        # self.lock = Thread.Lock()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def startMeas(self, sidList):
        print("CTRL REFL: Start Meas for "+sidList)
        self.counter[sidList] = 0
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("CTRL REFL: Stop Meas for "+sidList)
        self.startedMeas = False

    def doMeasure(self):
        # print("Do Meas ST:"+str(self.startedMeas))
        if self.startedMeas:
            print("CTRL REFL: Loss Probe / Color")
            for sl in self.counter:
                self.counter[sl] += 1
        self.scheduler.enter(2, 1, self.doMeasure)

    def getMeas(self, sidList):
        print("CTRL REFL: Get Mead Data for "+sidList)
        return self.counter[sidList]

    def run(self):
        print("Thread '" + self.name + "' start")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("Thread '" + self.name + "' stop")

    def receveQuery(self, message):
        print("Received Query")



class TWAMPController(srv6pmService_pb2_grpc.SRv6PMServicer):
    def __init__(self, SessionSender,SessionReflector): 
        self.port_server = 20000 
        self.sender = SessionSender
        self.reflector = SessionReflector

    def startExperimentSender(self, request, context):
        print("REQ - startExperiment")
        self.sender.startMeas(request.sdlist)
        status = srv6pmCommons_pb2.StatusCode.Value('STATUS_SUCCESS')
        return srv6pmSender_pb2.StartExperimentSenderReply(status=status)

    def stopExperimentSender(self, request, context):
        print("REQ - stopExperiment")
        self.sender.stopMeas(request.sdlist)
        status = srv6pmCommons_pb2.StatusCode.Value('STATUS_SUCCESS')
        return srv6pmCommons_pb2.StopExperimentReply(status=status)

    def startExperimentReflector(self, request, context):
        print("REQ - startExperiment")
        self.reflector.startMeas(request.sdlist)
        status = srv6pmCommons_pb2.StatusCode.Value('STATUS_SUCCESS')
        return srv6pmReflector_pb2.StartExperimentReflectorReply(status=status)

    def stopExperimentReflector(self, request, context):
        print("REQ - stopExperiment")
        self.reflector.stopMeas(request.sdlist)
        status = srv6pmCommons_pb2.StatusCode.Value('STATUS_SUCCESS')
        return srv6pmCommons_pb2.StopExperimentReply(status=status)

    def retriveExperimentResults(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.sender.getMeas(request.sdlist)
        status = srv6pmCommons_pb2.StatusCode.Value('STATUS_SUCCESS')
        response = srv6pmCommons_pb2.ExperimentDataResponse(status=status)
        data = response.measurement_data.add()
        data.sender_tx_counter = res
        return response


def serve(ipaddr,gprcPort,recvInterf):
    sessionsender = SessionSender()
    sessionreflector = SessionReflector()
    packetRecv = TestPacketReceiver(recvInterf,sessionsender,sessionreflector)
    sessionreflector.start()
    sessionsender.start()
    packetRecv.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmService_pb2_grpc.add_SRv6PMServicer_to_server(TWAMPController(sessionsender,sessionreflector), server)
    srv6_manager_pb2_grpc.add_SRv6ManagerServicer_to_server(
        SRv6Manager(), server)
    server.add_insecure_port("[{ip}]:{port}".format(ip=ipaddr,port=gprcPort))
    print("\n-------------- Start Demon --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    ipaddr =  sys.argv[1]
    gprcPort =  sys.argv[2]
    recvInterf =  sys.argv[3]

    logging.basicConfig()
    serve(ipaddr,gprcPort,recvInterf)
