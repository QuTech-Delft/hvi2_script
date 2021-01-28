# -*- coding: utf-8 -*-
"""
Created on Fri Jun 12 12:14:43 2020

@author: sdesnoo
"""

class ModuleRegister:
    '''
    Module register representing multiple registers with the same name across modules.
    Example:
        nrepeat_reg = hvi.add_module_register(module_aliases=['awg1','awg2','dig1'])
        # write value to hardware for every module with this register.
        nrepeat_reg.write(10)
    '''
    def __init__(self, register_dict):
        self.registers = register_dict

