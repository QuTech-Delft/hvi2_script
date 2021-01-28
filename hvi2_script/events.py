"""
@author: sdesnoo
"""
from keysight_hvi import Condition

from .operand import Operand
from .conditions import HviCondition

class Event(Operand, HviCondition):
    def __init__(self, engine_name, kt_event):
        self.engine_name = engine_name
        self.kt_event = kt_event
        self.number_conditions = 1
        self.kt_condition = Condition.event(kt_event)

    @property
    def kt_operand(self):
        return self.kt_event

    @property
    def name(self):
        return self.kt_event.name

    @property
    def full_name(self):
        return f'[{self.engine_name}|{self.kt_event.name}({self.kt_event.hw_name})]'

    def __repr__(self):
        return f'[{self.kt_event.name}]'
