# -*- coding: utf-8 -*-
"""
Created on Sun May 31 17:41:44 2020

@author: sdesnoo
"""

class Expression:
    def __init__(self, lhs, operator, rhs):
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs
        self.destination = None

    def __repr__(self):
        return f'{self.destination} = {self.lhs} {self.operator} {self.rhs}'

