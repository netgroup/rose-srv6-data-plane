#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import datetime
import logging
from structlog import wrap_logger, get_logger
from structlog.processors import JSONRenderer
from structlog.stdlib import filter_by_level, add_log_level, LoggerFactory
import structlog


# da fare solo una volta nel progetto

LOGFILE = "/var/log/srv6/srv6.log"  # mettere un path

logging.basicConfig(format='%(message)s', level="INFO", filename=LOGFILE)
structlog.configure(
    logger_factory=LoggerFactory(),
    processors=[
        structlog.processors.JSONRenderer(
            indent=1,
            sort_keys=True)])


MN = 100
# da fare quando vogliamo fare log
log = get_logger()
log.info(measure_id=MN, measure_type="loss", loss=0.4)

# alternativamente alcuni campi che si ripetono possiamo specificarli una
# volta sola

MN += 1
log = get_logger(measure_id=MN)
log.info(measure_type="loss", loss=0.5)
log.info(measure_type="loss", loss=0.7, nuovocampoinventato="pippo")
log.info(measure_type="loss", loss=0.9, nuovocampoinventato="pippo")

MN += 1
meas = {"measure_id": MN, "measure_type": "loss"}

log = get_logger(**meas)
log.info(loss=0.5)
log.info(loss=0.7, c1=123434, c2=123435)
log.info(loss=0.9, c1=5677, c2=1234566, c3=5677, c4=555)
