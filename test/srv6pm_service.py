#!/usr/bin/python
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmService_pb2_grpc
import srv6pmService_pb2
from concurrent import futures
import grpc
import logging
import logging.config


class Servicer(srv6pmService_pb2_grpc.SRv6PMServicer):

    def startExperimentSender(self, request, context):
        logger.info('Service startExperimentSender')
        res = 1
        return srv6pmService_pb2.StartExperimentSenderReply(status=res)

    def startExperimentReflector(self, request, context):
        logger.info('Service startExperimentSender')
        res = 1
        return srv6pmService_pb2.StartExperimentReflectorReply(status=res)

    def stopExperiment(self, request, context):
        logger.info('Service stopExperiment')
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def retriveExperimentResults(self, request, context):
        logger.info('Service retriveExperimentResults')
        return srv6pmCommons_pb2.ExperimentDataResponse(status=res)


def serve():
    sender_end_point = 'localhost:50052'
    serverSender = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    srv6pmSender_pb2_grpc.add_SRv6PMSenderServicer_to_server(
        SenderServicer(), serverSender)
    serverSender.add_insecure_port(sender_end_point)
    serverSender.start()
    logger.info('Sender service running on: %s', sender_end_point)
    serverSender.wait_for_termination()


if __name__ == '__main__':
    # create logger
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('srv6pm')

    serve()
