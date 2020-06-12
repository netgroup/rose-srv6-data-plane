#!/usr/bin/python


def set_punt(sid_list):
    mod_list = sid_list
    mod_list[0] = mod_list[0][:-3] + "200"
    return mod_list


def rem_punt(sid_list):
    mod_list = sid_list
    mod_list[0] = mod_list[0][:-3] + "100"
    return mod_list


def sid_list_converter(sid_list):
    return ",".join(sid_list)
