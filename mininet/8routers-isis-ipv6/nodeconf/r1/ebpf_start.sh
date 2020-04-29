#!/bin/bash

### !!! DO NOT CALL THIS FILE DIRECTLY !!! ###
if [ -z "${EBPF_START+x}" ]; then 
	echo "EBPF_START is unset. Do not call this script directly"
	exit 1
fi

EBPF_HELPER="$CDIR/ebpf_helper.sh"
source "${EBPF_HELPER}"

prepare_netdev r1-r2
move_ip_addr r1-r2

ZEBRA_CFG="$(prepare_daemon_conf "$WDIR/zebra.conf" r1-r2)" \
	|| { echo "Error during the creation of ebpf zebra .conf"; exit 1; }

ISIS_CFG="$(prepare_daemon_conf "$WDIR/isisd.conf" r1-r2)" \
	|| { echo "Error during the creation of ebpf isisd .conf"; exit 1; }
