"""
@author: sdesnoo
"""
from keysight_hvi import Condition

class HviCondition:

    def __init__(self, number_conditions):
        self.number_conditions = number_conditions
        self.kt_condition = None

    '''
    The condition clas binds the python  bitwise and '&', or '|' and not '~' operators to HVI conditions.
    '''
    def __and__(self, rhs):
        kt_condition = Condition.logical_and([self.kt_condition, rhs.kt_condition])
        return ConditionalExpression(self, 'AND', rhs, kt_condition)

    def __or__(self, rhs):
        kt_condition = Condition.logical_or([self.kt_condition, rhs.kt_condition])
        return ConditionalExpression(self, 'OR', rhs, kt_condition)

    def __invert__(self):
        kt_condition = Condition.logical_not(self.kt_condition)
        return UnaryConditionalExpression('NOT', self, kt_condition)


class ConditionalExpression(HviCondition):
    def __init__(self, lhs, operator, rhs, kt_condition):
        super().__init__(lhs.number_conditions + rhs.number_conditions)
        self.kt_condition = kt_condition
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs

    def __repr__(self):
        return f'({self.lhs} {self.operator} {self.rhs})'


class UnaryConditionalExpression(HviCondition):
    def __init__(self, operator, operand, kt_condition):
        super().__init__(operand.number_conditions + 1)
        self.kt_condition = kt_condition
        self.operator = operator
        self.operand = operand

    def __repr__(self):
        return f'{self.operator}({self.operand})'
