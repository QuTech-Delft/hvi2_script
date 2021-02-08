from typing import Dict

from keysight_hvi import ComparisonOperator, Condition
from .module_builder import ModuleSequenceBuilder
from .builders_base import SequenceBuilder, SequenceBlock, SyncedBlock, BuilderState
from .instruction_timing import InstructionTiming, calculate_start_delay
from .flow import Sequence, BranchingStatement, SyncBlockStatement
from .operand import kt_operand


class SyncSequenceBuilder(SequenceBuilder):

    def __init__(self, sequencer, kt_sync_sequence, module_builders:Dict[str,ModuleSequenceBuilder]):
        super().__init__()
        self.sequencer = sequencer
        main_entry_latency_ns = 30
        self._main = Sequence(None, kt_sync_sequence, self.line, main_entry_latency_ns)
        self.module_builders = module_builders
        self.master_engine_alias = self.sequencer.system._master_engine.alias
        self.propagation_delay_ticks = 10 # this is for 1 chassis.

    def Main(self):
        self._state = BuilderState.AWAIT_ENTER
        return SequenceBlock(self, None, self._main)

    def _add_while(self, kt_condition, n_conditions, text):
        # always use 2 for end latency of last statement. Add empty SyncMultiSequenceBlock to realize this.
        end_latency_last_statement = 2
        timing = InstructionTiming(3+n_conditions,
                                   start_latency=5+n_conditions+self.propagation_delay_ticks,
                                   entry_latency=14+self.propagation_delay_ticks+end_latency_last_statement,
                                   end_latency=14+n_conditions+self.propagation_delay_ticks+end_latency_last_statement,
                                   iteration_overhead=5+n_conditions)
        min_start_delay = calculate_start_delay(self.sequence.min_start_delay_next, timing)
        start_delay = min_start_delay

        line = self.line
        while_statement = self.kt_sequence.add_sync_while(f'{line}:sync_{text}', start_delay, kt_condition)
        loop_seq = Sequence(self.sequence, while_statement.sync_sequence, line, timing.entry_latency_ns)
        statement = BranchingStatement(line, self.sequence, start_delay, text, min_start_delay, timing)
        statement.append_sequence(loop_seq)
        self._append_statement(statement)

        self._state = BuilderState.AWAIT_ENTER
        return SequenceBlock(self, statement, loop_seq)

    def While(self, condition):
        text = f'while {condition}:'
        n_conditions = condition.number_conditions

        return self._add_while(condition.kt_condition, n_conditions, text)

    def Repeat(self, n):
        register = self.sequencer.add_sync_register(f'counter_{self.line}')

        with self.SyncedModules():
            self.module_builders[self.master_engine_alias].set_register(register, 0)

        text = f'while {register.full_name} < {n}:'

        condition = Condition.register_comparison(kt_operand(register), ComparisonOperator.LESS_THAN, kt_operand(n))
        n_conditions = 1

        block = self._add_while(condition, n_conditions, text)
        # Note: sequence block can be entered multiple times
        with block:
            with self.SyncedModules():
                self.module_builders[self.master_engine_alias].increment_register(register)

        self._state = BuilderState.AWAIT_ENTER
        return block

    def SyncedModules(self):
        '''
        Create block with synchronized sequences per module
        '''
        timing = InstructionTiming(0,
                                   entry_latency=2, # @@@ documentation: entry_latency=1,
                                   end_latency=1)
        min_start_delay = calculate_start_delay(self.sequence.min_start_delay_next, timing)
        start_delay = min_start_delay

        line = self.line
        sync_block = self.kt_sequence.add_sync_multi_sequence_block(f'{line}:sync_block', start_delay)

        block_statement = SyncBlockStatement(line, self.sequence, start_delay, '='*30, min_start_delay, timing)

        self._append_statement(block_statement)

        module_sequences = []
        for engine_alias, module_builder in self.module_builders.items():
            module_line_number = line + module_builder.module_id
            sequence = Sequence(self.sequence,
                                sync_block.sequences[engine_alias],
                                module_line_number,
                                timing.entry_latency_ns)
            block_statement.append_sequence(engine_alias, sequence)
            module_sequences.append((module_builder, sequence))

        self._state = BuilderState.AWAIT_ENTER
        return SyncedBlock(self, block_statement, module_sequences)


    def __getitem__(self, name):
        registers = self.sequencer.registers()
        if name in registers:
            return registers[name]
        raise AttributeError(f"sync sequence has no register '{name}'")

    def __setitem__(self, name, value):
        registers = self.sequencer.registers()
        if name not in registers:
            raise AttributeError(f"sync sequence has no register '{name}'")
        register = registers[name]
        with self.SyncedModules():
            self.module_builders[self.master_engine_alias].assign_register(register, value)

    # @@@ add register sharing

