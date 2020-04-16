#!/usr/bin/python
import srv6pmCommons_pb2_grpc
import srv6pmCommons_pb2
import srv6pmSender_pb2_grpc
import srv6pmSender_pb2
from concurrent import futures
import grpc
import logging
import logging.config


class SenderServicer(srv6pmSender_pb2_grpc.SRv6PMSenderServicer):

    def startExperiment(self, request, context):
        logger.info('Sender service startExperiment')
        res = 1
        return srv6pmSender_pb2.StartExperimentSenderReply(status=res)

    def stopExperiment(self, request, context):
        logger.info('Sender service stopExperiment')
        res = 1
        return srv6pmCommons_pb2.StopExperimentReply(status=res)

    def retriveExperimentResults(self, request, context):
        logger.info('Sender service retriveExperimentResults')
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
