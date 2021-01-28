"""
@author: sdesnoo
"""

class Operand:
    '''
    Base class to wrap Keysight HVI objects that can be used as an operand, e.g. KtHviRegister.
    '''
    @property
    def kt_operand(self):
        raise NotImplementedError()


def kt_operand(x):
    '''
    Returns the literal or the KtHvi object that can be used as operand in KtHvi instructions.
    '''
    if isinstance(x, Operand):
        return x.kt_operand
    # assume it is a constant (float or double)
    return x
