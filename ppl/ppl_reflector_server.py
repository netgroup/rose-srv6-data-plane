#!/usr/bin/python
from concurrent import futures

import grpc
import logging
from threading import Thread
import sched
import sys
import os
import time


import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmCommons_pb2
import srv6pmCommons_pb2_grpc


class MeasCtrlReflector(Thread):
    def __init__(self, name):
        Thread.__init__(self)
        self.name = name
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
                self.counter[sl] += 10
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


class ReflectorServicer(srv6pmReflector_pb2_grpc.SRv6PMReflectorr):
    def __init__(self, measCtrlRefl):
        self.port_server = 1234
        self.measCtrlRefl = measCtrlRefl

    def startExperiment(self, request, context):
        print("REQ - startExperiment")
        self.measCtrlRefl.startMeas(request.sdlist)
        return srv6pmReflector_pb2.StartExperimentReflectorReply(status=1)

    def stopExperiment(self, request, context):
        print("REQ - stopExperiment")
        self.measCtrlRefl.stopMeas(request.sdlist)
        return srv6pmCommons_pb2.StopExperimentReply(status=1)

    def retriveExperimentResults(self, request, context):
        print("REQ - retriveExperimentResults")
        res = self.measCtrlRefl.getMeas(request.sdlist)
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve():
    thMeasRefl = MeasCtrlReflector("MeasCtrlReflector")
    thMeasRefl.start()
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmReflector_pb2_grpc.add_SRv6PMReflectorr_to_server(
        ReflectorServicer(thMeasRefl), server)
    server.add_insecure_port('10.1.1.2:50052')
    print("\n-------------- Reflector Sarted --------------\n")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
