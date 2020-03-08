#!/usr/bin/python
from concurrent import futures
import grpc
import logging
import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc


class ReflectorServicer(srv6pmReflector_pb2_grpc.SRv6PMReflectorServiceServicer):

    def __init__(self):
        self.port_server = 1234

    def startExperiment(self, request, context):
        
        return srv6pmReflector_pb2.StartExperimentReflectorReply(status=15)

    def stopExperiment(self, request, context):
        
        return srv6pmReflector_pb2.StopExperimentReflectorReply(status=0)

    def retriveExperimentResults(self, request, context):
        
        return srv6pmReflector_pb2.RetriveExperimentDataReply(status=0)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmReflector_pb2_grpc.add_SRv6PMReflectorServiceServicer_to_server(
        ReflectorServicer(), server)
    server.add_insecure_port('127.0.0.1:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    serve()
