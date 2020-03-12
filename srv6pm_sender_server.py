#!/usr/bin/python
from concurrent import futures
import grpc
import logging
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc


class SenderServicer(srv6pmSender_pb2_grpc.SRv6PMSenderServiceServicer):

    def __init__(self):
        self.port_server = 1234

    def startExperiment(self, request, context):
        
        x = 10
        i = 0
        while i<10:
                x = x + 2
                i += 1

        return srv6pmSender_pb2.StartExperimentSenderReply(status=x)

    def stopExperiment(self, request, context):
        
        return srv6pmSender_pb2.StopExperimentSenderReply(status=0)

    def retriveExperimentResults(self, request, context):
        
        return srv6pmSender_pb2.RetriveExperimentDataReply(status=0)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmSender_pb2_grpc.add_SRv6PMSenderServiceServicer_to_server(
        SenderServicer(), server)
    server.add_insecure_port('127.0.0.1:50052')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
