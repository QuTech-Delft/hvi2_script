"""
@author: sdesnoo
"""

from .instruction_timing import calculate_start_delay
from .flow import Statement

class BuilderState:
    CLOSED = 0
    NOT_ACTIVE = 1
    ACTIVE = 2
    AWAIT_ENTER = 3

class SequenceBuilder():

    def __init__(self):
        self.line_prefix = ''
        self.line_counter = 0
        self.sequence_stack = []
        self._state = BuilderState.NOT_ACTIVE

    def set_state(self, state):
        self._state = state

    def check_state(self):
        if self._state == BuilderState.CLOSED:
            raise Exception('Sequence builder is closed')
        if self._state == BuilderState.NOT_ACTIVE:
            raise Exception('Syntax error: Not in active scope')
        if self._state == BuilderState.AWAIT_ENTER:
            raise Exception('Syntax error: expected with-statement')

    @property
    def line(self):
        return f'{self.line_prefix}{self.line_counter+1}'

    def increment_line_counter(self):
        self.line_counter += 1

    @property
    def sequence(self):
        return self.sequence_stack[-1]

    @property
    def _current_statement(self):
        return self.sequence.statements[-1]

    @property
    def kt_sequence(self):
        return self.sequence.kt_sequence

    def start_sequence(self, sequence, line_prefix):
        if self._state != BuilderState.NOT_ACTIVE or len(self.sequence_stack) > 0:
            raise Exception(f'syntax error on line {self.line}')
        self.sequence_stack.append(sequence)
        self.line_prefix = line_prefix
        self.line_counter = 0
        self.set_state(BuilderState.ACTIVE)

    def enter_sequence(self, sequence):
        if self._state != BuilderState.AWAIT_ENTER:
            raise Exception(f'syntax error on line {self.line}')
        self.set_state(BuilderState.ACTIVE)
        self.sequence_stack.append(sequence)

    def exit_sequence(self):
        # @@@ determine sequence duration
        # Note: sequence can be entered multiple times, e.g. repeat counter increment
        self.sequence_stack.pop()
        if len(self.sequence_stack) > 0:
            branch_statement = self.sequence.statements[-1]
            branch_tail = max(sequence.tail for sequence in branch_statement.sequences)
            self.sequence.tail = branch_statement.timing_constraints.get_tail_ns() + branch_tail
        else:
            self.set_state(BuilderState.NOT_ACTIVE)

    def _append_statement(self, statement):
        self.check_state()
        self.sequence.append_statement(statement)
        self.increment_line_counter()

    def add_statement(self, text, timing, start_delay=None):
        min_start_delay = calculate_start_delay(self.sequence.min_start_delay_next, timing)
        if start_delay is None:
            start_delay = min_start_delay
        if start_delay < min_start_delay:
            raise Exception(f'delay too short; minimum delay (start_delay): {min_start_delay}')

        statement = Statement(self.line, self.sequence, start_delay, text, start_delay, timing)
        self._append_statement(statement)
        return statement


class SequenceBlock:
    def __init__(self, builder, statement, sequence):
        self.builder = builder
        self.statement = statement
        self.sequence = sequence

    def __enter__(self):
        self.builder.enter_sequence(self.sequence)
        return self.statement

    def __exit__(self, type, value, traceback):
        self.builder.exit_sequence()
        if self.statement is not None:
            s = self.statement
            s.non_deterministic = \
                f'N_{s.line}*({self.sequence.total_duration()} + {s.timing_constraints.iteration_overhead_ns})'


class SyncedBlock:
    def __init__(self, builder, block_statement, module_sequences):
        self.builder = builder
        self.block_statement = block_statement
        self.module_sequences = module_sequences

    def __enter__(self):
        for module_builder,sequence in self.module_sequences:
            module_builder.start_sequence(sequence, sequence.line)
        self.builder.set_state(BuilderState.NOT_ACTIVE)
        return self.block_statement

    def __exit__(self, type, value, traceback):
        self.builder.set_state(BuilderState.ACTIVE)
        seq_duration = []
        for module_builder,sequence in self.module_sequences:
            seq_duration.append(sequence.total_duration())
            module_builder.exit_sequence()
        # @@@ calculate exit time, timed/resync
        self.block_statement.non_deterministic = f'max({seq_duration})'
