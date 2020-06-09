from concurrent import futures
import grpc
import logging
import logging.config


import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc
import srv6pmCommons_pb2
import srv6pmCommons_pb2_grpc


def startExperimentSender(stub):
    request = srv6pmSender_pb2.StartExperimentSenderRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.startExperiment(request=request)


def retriveExperimentResultsSender(stub):
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.retriveExperimentResults(request=request)


def stopExperimentSender(stub):
    request = srv6pmCommons_pb2.StopExperimentRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.stopExperiment(request=request)


def startExperimentReflector(stub):
    request = srv6pmReflector_pb2.StartExperimentReflectorRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.startExperiment(request=request)


def stopExperimentReflector(stub):
    request = srv6pmCommons_pb2.StopExperimentRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.stopExperiment(request=request)


def retriveExperimentResultsReflector(stub):
    request = srv6pmCommons_pb2.RetriveExperimentDataRequest()
    request.sdlist = "fcff:2::1/fcff:3::1/fcff:4::1"
    return stub.retriveExperimentResults(request=request)


def test_reflector():
    with grpc.insecure_channel('localhost:50052') as channel2:
        sender = srv6pmSender_pb2_grpc.SRv6PMSenderStub(channel2)

        send_res = startExperimentSender(sender)

        send_res = stopExperimentReflector(sender)


if __name__ == '__main__':
    # create logger
    logging.config.fileConfig('logging.conf')
    logger = logging.getLogger('srv6pm')
    test_reflector()
