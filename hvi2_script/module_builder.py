"""
@author: sdesnoo
"""
from keysight_hvi import ComparisonOperator, Condition, FpgaRegisterDefinition, WaitMode, SyncMode

from .builders_base import SequenceBuilder, SequenceBlock, BuilderState
from .engines import HviEngine
from .instruction_timing import InstructionTiming, calculate_start_delay
from .flow import Statement, Sequence, BranchingStatement
from .operand import kt_operand
from .expressions import Expression
from .operators import BinaryOperator

class ModuleSequenceBuilder(SequenceBuilder):
    def __init__(self, engine:HviEngine, module_id:str, sequencer):
        '''
        module_id: char 'A' ... 'Z'
        '''
        super().__init__()
        self.engine = engine
        self.module_id = module_id
        self.sequencer = sequencer
        for name, extension in engine.extensions.items():
            setattr(self, name, extension(name, self))

    def _add_while(self, kt_condition, n_conditions, text):
        timing = InstructionTiming(3+n_conditions,
                                   start_latency=5+n_conditions,
                                   entry_latency=2,
                                   end_latency=6+n_conditions,
                                   iteration_overhead=5+n_conditions)
        min_start_delay = calculate_start_delay(self.sequence.min_start_delay_next, timing)
        start_delay = min_start_delay
        line = self.line
        while_statement = self.kt_sequence.add_while(f'{line}:{text}', start_delay, kt_condition)
        loop_seq = Sequence(self.sequence, while_statement.sequence, line, timing.entry_latency_ns)
        statement = BranchingStatement(line, self.sequence, start_delay, text, min_start_delay, timing)
        statement.append_sequence(loop_seq)
        self._append_statement(statement)

        self._state = BuilderState.AWAIT_ENTER
        return SequenceBlock(self, statement, loop_seq)

    def _add_actions(self, alias, action_list, timing, start_delay=None):
        action_execute = self.kt_sequence.instruction_set.action_execute
        instruction = self._add_instruction(start_delay, alias, action_execute, timing)
        instruction.set_parameter(action_execute.action.id, action_list)

    def _add_instruction(self, start_delay, text, instruction, timing):
        min_start_delay = calculate_start_delay(self.sequence.min_start_delay_next, timing)
        if start_delay is None:
            start_delay = min_start_delay
        if start_delay < min_start_delay:
            raise Exception(f'timing error at line {self.line}:{text} minimum: {min_start_delay}')
        instruction = self.kt_sequence.add_instruction(f'{self.line}:{text}', start_delay, instruction.id)
        statement = Statement(self.line, self.sequence, start_delay, text, min_start_delay, timing)
        self._append_statement(statement)
        return instruction

    def _add_hvi_instruction(self, text, instruction_name, timing, params, start_delay=None):
        instruction = getattr(self.kt_sequence.instruction_set, instruction_name)
        statement = self._add_instruction(start_delay, text, instruction, timing)
        for arg,value in params.items():
            statement.set_parameter(getattr(instruction, arg).id, kt_operand(value))

    def _add_engine_instruction(self, text, instruction_name, timing, params, start_delay=None):
        instruction = getattr(self.engine.instruction_set, instruction_name)
        statement = self._add_instruction(start_delay, text, instruction, timing)
        for arg,value in params.items():
            statement.set_parameter(getattr(instruction, arg).id, kt_operand(value))

    def _wait_register(self, register):
        text = f'wait {register}'
        timing = InstructionTiming(0, start_latency=2)
        statement = self.add_statement(text, timing)
        statement.non_deterministic = str(register)
        self.kt_sequence.add_wait_time(statement.alias, statement.start_delay, kt_operand(register))

    def _wait_constant(self, time):
        # delay statement is empty statement with start_delay
        text = f'wait {time} ns'
        timing = InstructionTiming(1)
        statement = self.add_statement(text, timing, start_delay=time)
        self.kt_sequence.add_delay(statement.alias, statement.start_delay)

    def wait(self, time):
        '''
        Adds a wait statement to the sequence.
        Args:
            time (int or register): time to wait in nanoseconds
        '''
        # Note: instruction name must be unique in sequence
        if isinstance(time, int):
            self._wait_constant(time)
        else:
            self._wait_register(time)
        return self._current_statement

    def wait_for(self, condition):
        text = f'wait for {condition}'
        timing = InstructionTiming(1, non_deterministic=f'{condition}')
        statement = self.add_statement(text, timing)
        kt_wait = self.kt_sequence.add_wait(statement.alias, statement.start_delay, condition.kt_condition)
        kt_wait.set_mode(WaitMode.VALUE, SyncMode.IMMEDIATE)

    def While(self, condition):
        text = f'while {condition}:'
        n_conditions = condition.number_conditions

        return self._add_while(condition.kt_condition, n_conditions, text)

    def Repeat(self, n):
        register = self.sequencer._add_register(self.engine.alias, f'counter_{self.line}')

        self.set_register(register, 0)

        text = f'while {register} < {n}:'

        condition = Condition.register_comparison(kt_operand(register), ComparisonOperator.LESS_THAN, kt_operand(n))
        n_conditions = 1

        block = self._add_while(condition, n_conditions, text)

        # Note: sequence block can be entered multiple times, but AWAIT_ENTER has to be reset
        with block:
            self.increment_register(register)

        self._state = BuilderState.AWAIT_ENTER
        return block

    def increment_register(self, register, value=1):
        self._add_hvi_instruction(
                f'{register} += {value}',
                'add',
                InstructionTiming(1, execution_time=8,
                                  resources=[register], dependencies=[register]),
                params={'destination':register,
                        'left_operand':register,
                        'right_operand':value}
                )

    def set_register(self, register, value):
        dependencies=[register]
        if not isinstance(value, int):
            dependencies.append(value)

        self._add_hvi_instruction(
                f'{register} = {value}',
                'assign',
                InstructionTiming(1, execution_time=5,
                                  resources=[register], dependencies=dependencies),
                params={'destination':register, 'source':value}
                )

    def assign_register(self, register, value):
        if isinstance(value, Expression):
            expression = value
            expression.destination = register
            if expression.operator == BinaryOperator.ADD:
                operation = self.kt_sequence.instruction_set.add
            elif expression.operator == BinaryOperator.SUB:
                operation = self.kt_sequence.instruction_set.subtract
            else:
                raise Exception('Unknown operator')

            dependencies=[]
            if not isinstance(expression.rhs, int):
                dependencies.append(expression.rhs)
            if not isinstance(expression.lhs, int):
                dependencies.append(expression.lhs)
            timing = InstructionTiming(1, execution_time=8,
                                       resources=[expression.destination], dependencies=dependencies)

            instruction = self._add_instruction(None, repr(expression), operation, timing)
            instruction.set_parameter(operation.left_operand.id, kt_operand(expression.lhs))
            instruction.set_parameter(operation.right_operand.id, kt_operand(expression.rhs))
            instruction.set_parameter(operation.destination.id, kt_operand(expression.destination))

        elif isinstance(value, FpgaRegisterDefinition):
            self._add_hvi_instruction(
                    f'{register} = fpga:{value.name}',
                    'fpga_register_read',
                    InstructionTiming(1, execution_time=4),
                    params={'destination':register, 'fpga_register':value}
                    )

        else:
            self.set_register(register, value)

    def __getitem__(self, name):
        registers = self.sequencer.engine_registers[self.engine.alias]
        if name not in registers:
            raise AttributeError(f"sequence has no register '{name}'")
        return registers[name]

    def __setitem__(self, name, value):
        registers = self.sequencer.engine_registers[self.engine.alias]
        if name not in registers:
            raise AttributeError(f"sequence has no register '{name}'")
        register = registers[name]
        self.assign_register(register, value)

    def write_fpga(self, fpga_register, value, text=None):
        if text is None:
            text = f'fpga:{fpga_register.name} = {value}'
        self._add_hvi_instruction(
                text,
                'fpga_register_write',
                InstructionTiming(1, execution_time=4),
                params={'fpga_register':fpga_register, 'value':value}
                )

    def write_fpga_indexed(self, fpga_memory_map, index, value, text=None):
        if text is None:
            text = f'fpga:{fpga_memory_map.name}[{index}] = {value}'
        self._add_hvi_instruction(
                text,
                'fpga_array_write',
                InstructionTiming(1, execution_time=4),
                params={
                        'fpga_memory_map':fpga_memory_map,
                        'fpga_memory_map_offset':index,
                        'value':value
                        }
                )

    def read_fpga_indexed(self, fpga_memory_map, index, destination, text=None):
        if text is None:
            text = f'{destination} = fpga:{fpga_memory_map.name}[{index}]'
        self._add_hvi_instruction(
                text,
                'fpga_array_read',
                InstructionTiming(1, execution_time=4),
                params={
                        'fpga_memory_map':fpga_memory_map,
                        'fpga_memory_map_offset':index,
                        'destination':destination
                        }
                )
