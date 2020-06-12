#!/usr/bin/python
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmSender_pb2_grpc
import srv6pmSender_pb2
from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time


class MeasReceiver(Thread):
    def __init__(self, name, ctrl):
        Thread.__init__(self)
        self.name = name
        self.measCtrl = ctrl

    def packetRecvCallback(self):
        print("Packets Recv Callback")
        message = ""
        self.measCtrl.receveQueryResponse(message)

    def run(self):
        print("Receiving Packets")
        # codice netqueue


class MeasCtrl(Thread):
    def __init__(self, name):
        Thread.__init__(self)
        self.name = name
        self.startedMeas = False
        self.counter = {}
        # self.lock = Thread.Lock()
        self.scheduler = sched.scheduler(time.time, time.sleep)

    def startMeas(self, sidList):
        print("CTRL: Start Meas for " + sidList)
        self.counter[sidList] = 0
        self.startedMeas = True

    def stopMeas(self, sidList):
        print("CTRL: Stop Meas for " + sidList)
        self.startedMeas = False

    def doMeasure(self):
        if self.startedMeas:
            print("CTRL: Loss Probe / Color")
            for sl in self.counter:
                self.counter[sl] += 1
        self.scheduler.enter(2, 1, self.doMeasure)

    def getMeas(self, sidList):
        print("CTRL: Get Mead Data for " + sidList)
        return self.counter[sidList]

    def run(self):
        print("Thread '" + self.name + "' inizio")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("Thread '" + self.name + "' fine")

    def receveQueryResponse(self, message):
        print("Received response")


class SenderServicer(srv6pmSender_pb2_grpc.SRv6PMSenderServiceServicer):

    def __init__(self, measCtrl):
        self.port_server = 1234
        self.measCtrl = measCtrl

    def startExperiment(self, request, context):
        print("REQ - startExperiment")
        self.measCtrl.startMeas(request.sdlist)
        res = 1
        return srv6pmSender_pb2.StartExperimentSenderReply(status=res)

    def stopExperiment(self, request, context):
        print("REQ - stopExperiment")
        self.measCtrl.stopMeas(request.sdlist)
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def retriveExperimentResults(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.measCtrl.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve():
    thMeas = MeasCtrl("")
    thMeas.start()
    thMeasRecv = MeasReceiver("", thMeas)
    thMeasRecv.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmSender_pb2_grpc.add_SRv6PMSenderServiceServicer_to_server(
        SenderServicer(thMeas), server)
    server.add_insecure_port('10.1.1.1:50050')
    print("\n-------------- SRV6 PM Demon Started --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
