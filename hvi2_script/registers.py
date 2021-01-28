"""
@author: sdesnoo
"""
from keysight_hvi import Condition

from .operand import kt_operand, Operand
from .conditions import HviCondition
from .operators import RelationalOperator, BinaryOperator
from .expressions import Expression

class Register(Operand):
    '''
    Wrapper around KtHviRegister to add python operators (+,-,>,<,==,>=,<=,!=) to it.
    '''
    def __init__(self, engine_name, kt_register, initial_value):
        self.engine_name = engine_name
        self.kt_register = kt_register
        self.initial_value = initial_value

    @property
    def kt_operand(self):
        return self.kt_register

    @property
    def name(self):
        return self.kt_register.name

    @property
    def full_name(self):
        return f'[{self.engine_name}|{self.kt_register.name}]'

    def __repr__(self):
        return f'[{self.kt_register.name}]'

    def __eq__(self, rhs):
        return RegisterCondition(self, RelationalOperator.EQUAL_TO, rhs)

    def __ne__(self, rhs):
        return RegisterCondition(self, RelationalOperator.NOT_EQUAL_TO, rhs)

    def __gt__(self, rhs):
        return RegisterCondition(self, RelationalOperator.GREATER_THAN, rhs)

    def __ge__(self, rhs):
        return RegisterCondition(self, RelationalOperator.GREATER_THAN_OR_EQUAL_TO, rhs)

    def __lt__(self, rhs):
        return RegisterCondition(self, RelationalOperator.LESS_THAN, rhs)

    def __le__(self, rhs):
        return RegisterCondition(self, RelationalOperator.LESS_THAN_OR_EQUAL_TO, rhs)

    def __add__(self, rhs):
        return Expression(self, BinaryOperator.ADD, rhs)

    def __radd__(self, lhs):
        return Expression(lhs, BinaryOperator.ADD, self)

    def __sub__(self, rhs):
        return Expression(self, BinaryOperator.SUB, rhs)

    def __rsub__(self, lhs):
        return Expression(lhs, BinaryOperator.SUB, self)



class RegisterCondition(HviCondition):
    def __init__(self, register, operator, rhs):
        super().__init__(1)
        kt_condition = Condition.register_comparison(kt_operand(register), operator.kt_operator, kt_operand(rhs))
        self.kt_condition = kt_condition
        self.lhs = register
        self.operator = operator
        self.rhs = rhs

    def __repr__(self):
        return f'{self.lhs} {self.operator} {self.rhs}'


