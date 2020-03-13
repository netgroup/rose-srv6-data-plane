from concurrent import futures
import grpc
import logging
import srv6pmReflector_pb2
import srv6pmReflector_pb2_grpc
import srv6pmSender_pb2
import srv6pmSender_pb2_grpc

def startExperimentReflector(stub):
    request = srv6pmReflector_pb2.StartExperimentReflectorRequest()
    request.sdlist = "AD"
    #stub.startExperiment(request=request)
    return stub.startExperiment(request=request)
    

def stopExperimentReflector(stub):
    request = srv6pmReflector_pb2.StopExperimentReflectorRequest()
    request.sdlist = "AD"
  
    return stub.stopExperiment(request=request)

def retriveExperimentResults(stub):
    request = srv6pmReflector_pb2.RetriveExperimentReflectorRequest()
    request.sdlist = "AD"
  
    return stub.retriveExperiment(request=request)

def startExperimentSender(stub):
    request = srv6pmSender_pb2.StartExperimentSenderRequest()
    request.sdlist = "AD"
    #stub.startExperiment(request=request)
    return stub.startExperiment(request=request)



def createTunnelSender(stub):
    request = srv6pmSender_pb2.SRv6EPRequestSender()
    request.prefix = "AD"
    request.encapmode= "AD"
    request.segments = "AD"
    request.device = "AD"
    #stub.startExperiment(request=request)
    return stub.CreateSRv6TunnelSender(request=request)


def createTunnelReflector(stub):
    request = srv6pmReflector_pb2.SRv6EPRequestReflector()
    request.prefix = "AD"
    request.encapmode= "AD"
    request.segments = "AD"
    request.device = "AD"
    #stub.startExperiment(request=request)
    return stub.CreateSRv6TunnelReflector(request=request)



def run_ipv6():

    with grpc.insecure_channel('127.0.0.1:50051') as channel:
        stub = srv6pmReflector_pb2_grpc.SRv6PMReflectorServiceStub(channel)
        print("\n-------------- creationTunnelReflector --------------\n")
        reflector_res = createTunnelReflector(stub)
        
    if reflector_res!=None:
        print(reflector_res.status)     
    else: 
        print ("ERROR")



    with grpc.insecure_channel('127.0.0.1:50052') as channel:
        stub = srv6pmSender_pb2_grpc.SRv6PMSenderServiceStub(channel)
        print("\n-------------- creationTunnelSender --------------\n")
        sender_res = createTunnelSender(stub)

    if sender_res!=None:
        print(sender_res.status)        #stampo pacchetti sender
    else: 
        print ("ERROR")








def run():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel('127.0.0.1:50051') as channel:
        stub = srv6pmReflector_pb2_grpc.SRv6PMReflectorServiceStub(channel)
        print("\n-------------- startExperimentReflector --------------\n")
        reflector_res = startExperimentReflector(stub)
        
    if reflector_res!=None:
        print(reflector_res.status)     #stampo pacchetti reflector
    else: 
        print ("ERROR")

    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel('127.0.0.1:50052') as channel:
        stub = srv6pmSender_pb2_grpc.SRv6PMSenderServiceStub(channel)
        print("\n-------------- startExperimentSender --------------\n")
        sender_res = startExperimentSender(stub)

    if sender_res!=None:
        print(sender_res.status)        #stampo pacchetti sender
    else: 
        print ("ERROR")
    print("\n-------------- packet lost --------------\n")

    loss=sender_res.status-reflector_res.status     #calcolo perdita

    print (loss)






if __name__ == '__main__':
    logging.basicConfig()
    run_ipv6()
  #  run() 
    
