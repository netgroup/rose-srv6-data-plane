#!/usr/bin/python


from concurrent import futures
import grpc
import logging
from threading import Thread
import sched
import time

import srv6pm_grpc.srv6pmCommons_pb2
import srv6pm_grpc.srv6pmCommons_pb2_grpc
import srv6pm_grpc.srv6pmSender_pb2
import srv6pm_grpc.srv6pmSender_pb2_grpc


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
        print("Thread '" + self.name + "' start")
        self.scheduler.enter(2, 1, self.doMeasure)
        self.scheduler.run()
        print("Thread '" + self.name + "' stop")

    def receveQueryResponse(self, message):
        print("Received response")


class SenderServicer(srv6pmSender_pb2_grpc.SRv6PMSenderServicer):

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
    thMeas = MeasCtrl("MeasCtrl")
    thMeas.start()
    thMeasRecv = MeasReceiver("", thMeas)
    thMeasRecv.start()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmSender_pb2_grpc.add_SRv6PMSenderServicer_to_server(
        SenderServicer(thMeas), server)
    server.add_insecure_port('localhost:50052')
    print("\n-------------- Server Sarted --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
