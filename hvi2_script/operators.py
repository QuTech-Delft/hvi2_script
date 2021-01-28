"""
@author: sdesnoo
"""
from keysight_hvi import ComparisonOperator

class Operator:

    def __init__(self, kt_operator, symbol):
        self.kt_operator = kt_operator
        self.symbol = symbol

    def __repr__(self):
        return self.symbol

class RelationalOperator:
    EQUAL_TO = Operator(ComparisonOperator.EQUAL_TO, '==')
    NOT_EQUAL_TO = Operator(ComparisonOperator.NOT_EQUAL_TO, '!=')
    GREATER_THAN = Operator(ComparisonOperator.GREATER_THAN, '>')
    GREATER_THAN_OR_EQUAL_TO = Operator(ComparisonOperator.GREATER_THAN_OR_EQUAL_TO, '>=')
    LESS_THAN = Operator(ComparisonOperator.LESS_THAN, '<')
    LESS_THAN_OR_EQUAL_TO = Operator(ComparisonOperator.LESS_THAN_OR_EQUAL_TO, '<=')


class BinaryOperator:
    ADD = Operator('+','+')
    SUB = Operator('-', '-')

