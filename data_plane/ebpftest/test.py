#!/usr/bin/python

import time
import os
import sys

from xdp_srv6_pfplm_helper_user import EbpfPFPLM,EbpfException


def main():
    ifname = "veth3_egr"
    segs = "fcff:3::1,fcff:4::1,fcff:5::1"
    color = 1
    try: 
        obj = EbpfPFPLM()
        # FIXME: we need to find out a better way to expose such flags...
        obj.pfplm_load(ifname, obj.lib.F_VERBOSE | obj.lib.F_FORCE)

        obj.pfplm_change_active_color(ifname, color);

        c = obj.pfplm_get_active_color(ifname)
        print("color {d}\n".format(d=c))

        # Add flows and removes it soon after, just to test if they work
        obj.pfplm_add_flow(ifname, segs)
        obj.pfplm_del_flow(ifname, segs)

        obj.pfplm_add_flow(ifname, segs)

        while True:
            packets = 0
            colour = 1

            packets = obj.pfplm_get_flow_stats(ifname, segs, colour)

            print("dev {dev}, flow {flow}, packets {pkt} , color {color}".format(dev=ifname, flow=segs, pkt=packets, color=colour))
            time.sleep(1)

    except EbpfException as e:
        e.print_exception()

if __name__ == "__main__":
    main()