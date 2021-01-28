# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 18:39:39 2020

@author: sdesnoo
"""
try:
    import keysightSD1 as SD1
except:
    import sys
    sys.path.append(r'C:\Program Files (x86)\Keysight\SD1\Libraries\Python')
    import keysightSD1 as SD1


def check_error(result, s=''):
    if (type(result) is int and result < 0):
        print(SD1.SD_Error.getErrorMessage(result), result, s)
    return result

