# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: srv6pmReflector.proto

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


import srv6pmCommons_pb2 as srv6pmCommons__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='srv6pmReflector.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=b'\n\x15srv6pmReflector.proto\x1a\x13srv6pmCommons.proto\"\x85\x01\n\x1fStartExperimentReflectorRequest\x12\x0e\n\x06sdlist\x18\x01 \x01(\t\x12,\n\x11reflector_options\x18\x02 \x01(\x0b\x32\x11.ReflectorOptions\x12$\n\rcolor_options\x18\x03 \x01(\x0b\x32\r.ColorOptions\"<\n\x1dStartExperimentReflectorReply\x12\x1b\n\x06status\x18\x01 \x01(\x0e\x32\x0b.StatusCode\"Z\n\x10ReflectorOptions\x12\x30\n\x13mesurement_protocol\x18\x01 \x01(\x0e\x32\x13.MesurementProtocol\x12\x14\n\x0c\x64st_udp_port\x18\x02 \x01(\r2\x87\x02\n\x16SRv6PMReflectorService\x12U\n\x0fstartExperiment\x12 .StartExperimentReflectorRequest\x1a\x1e.StartExperimentReflectorReply\"\x00\x12@\n\x0estopExperiment\x12\x16.StopExperimentRequest\x1a\x14.StopExperimentReply\"\x00\x12T\n\x18retriveExperimentResults\x12\x1d.RetriveExperimentDataRequest\x1a\x17.ExperimentDataResponse\"\x00\x62\x06proto3'
  ,
  dependencies=[srv6pmCommons__pb2.DESCRIPTOR,])




_STARTEXPERIMENTREFLECTORREQUEST = _descriptor.Descriptor(
  name='StartExperimentReflectorRequest',
  full_name='StartExperimentReflectorRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='sdlist', full_name='StartExperimentReflectorRequest.sdlist', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='reflector_options', full_name='StartExperimentReflectorRequest.reflector_options', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='color_options', full_name='StartExperimentReflectorRequest.color_options', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=47,
  serialized_end=180,
)


_STARTEXPERIMENTREFLECTORREPLY = _descriptor.Descriptor(
  name='StartExperimentReflectorReply',
  full_name='StartExperimentReflectorReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='status', full_name='StartExperimentReflectorReply.status', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=182,
  serialized_end=242,
)


_REFLECTOROPTIONS = _descriptor.Descriptor(
  name='ReflectorOptions',
  full_name='ReflectorOptions',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='mesurement_protocol', full_name='ReflectorOptions.mesurement_protocol', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='dst_udp_port', full_name='ReflectorOptions.dst_udp_port', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=244,
  serialized_end=334,
)

_STARTEXPERIMENTREFLECTORREQUEST.fields_by_name['reflector_options'].message_type = _REFLECTOROPTIONS
_STARTEXPERIMENTREFLECTORREQUEST.fields_by_name['color_options'].message_type = srv6pmCommons__pb2._COLOROPTIONS
_STARTEXPERIMENTREFLECTORREPLY.fields_by_name['status'].enum_type = srv6pmCommons__pb2._STATUSCODE
_REFLECTOROPTIONS.fields_by_name['mesurement_protocol'].enum_type = srv6pmCommons__pb2._MESUREMENTPROTOCOL
DESCRIPTOR.message_types_by_name['StartExperimentReflectorRequest'] = _STARTEXPERIMENTREFLECTORREQUEST
DESCRIPTOR.message_types_by_name['StartExperimentReflectorReply'] = _STARTEXPERIMENTREFLECTORREPLY
DESCRIPTOR.message_types_by_name['ReflectorOptions'] = _REFLECTOROPTIONS
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

StartExperimentReflectorRequest = _reflection.GeneratedProtocolMessageType('StartExperimentReflectorRequest', (_message.Message,), {
  'DESCRIPTOR' : _STARTEXPERIMENTREFLECTORREQUEST,
  '__module__' : 'srv6pmReflector_pb2'
  # @@protoc_insertion_point(class_scope:StartExperimentReflectorRequest)
  })
_sym_db.RegisterMessage(StartExperimentReflectorRequest)

StartExperimentReflectorReply = _reflection.GeneratedProtocolMessageType('StartExperimentReflectorReply', (_message.Message,), {
  'DESCRIPTOR' : _STARTEXPERIMENTREFLECTORREPLY,
  '__module__' : 'srv6pmReflector_pb2'
  # @@protoc_insertion_point(class_scope:StartExperimentReflectorReply)
  })
_sym_db.RegisterMessage(StartExperimentReflectorReply)

ReflectorOptions = _reflection.GeneratedProtocolMessageType('ReflectorOptions', (_message.Message,), {
  'DESCRIPTOR' : _REFLECTOROPTIONS,
  '__module__' : 'srv6pmReflector_pb2'
  # @@protoc_insertion_point(class_scope:ReflectorOptions)
  })
_sym_db.RegisterMessage(ReflectorOptions)



_SRV6PMREFLECTORSERVICE = _descriptor.ServiceDescriptor(
  name='SRv6PMReflectorService',
  full_name='SRv6PMReflectorService',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=337,
  serialized_end=600,
  methods=[
  _descriptor.MethodDescriptor(
    name='startExperiment',
    full_name='SRv6PMReflectorService.startExperiment',
    index=0,
    containing_service=None,
    input_type=_STARTEXPERIMENTREFLECTORREQUEST,
    output_type=_STARTEXPERIMENTREFLECTORREPLY,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='stopExperiment',
    full_name='SRv6PMReflectorService.stopExperiment',
    index=1,
    containing_service=None,
    input_type=srv6pmCommons__pb2._STOPEXPERIMENTREQUEST,
    output_type=srv6pmCommons__pb2._STOPEXPERIMENTREPLY,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='retriveExperimentResults',
    full_name='SRv6PMReflectorService.retriveExperimentResults',
    index=2,
    containing_service=None,
    input_type=srv6pmCommons__pb2._RETRIVEEXPERIMENTDATAREQUEST,
    output_type=srv6pmCommons__pb2._EXPERIMENTDATARESPONSE,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_SRV6PMREFLECTORSERVICE)

DESCRIPTOR.services_by_name['SRv6PMReflectorService'] = _SRV6PMREFLECTORSERVICE

# @@protoc_insertion_point(module_scope)
