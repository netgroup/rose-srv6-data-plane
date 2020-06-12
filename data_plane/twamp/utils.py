#!/usr/bin/python


"""This module contains a collection of utilities used by several modules"""


def set_punt(sid_list):
    """Set PUNT to a SID list and return the new SID list"""
    mod_list = sid_list
    mod_list[0] = mod_list[0][:-3] + "200"
    return mod_list


def rem_punt(sid_list):
    """Remove PUNT from a SID list and return the new SID list"""

    mod_list = sid_list
    mod_list[0] = mod_list[0][:-3] + "100"
    return mod_list


def sid_list_converter(sid_list):
    """Convert list reporesentation of a SID list to a string representation"""
    return ",".join(sid_list)
