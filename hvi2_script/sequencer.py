import logging
import re
from functools import reduce
import time

from keysight_hvi import Sequencer, RegisterSize, CompilationFailed

from .system import HviSystem
from .hvi_exec import HviExec
from .registers import Register
from .module_registers import ModuleRegister
from .sync_builder import SyncSequenceBuilder
from .flow import BranchingStatement, SyncBlockStatement

class HviSequencer:
    '''
    HVI-2 Schedule builder.

    Example VideoMode:

        sequencer = HviSequencer(hvi_system)

        sequencer.add_module_register('duration', modules=awgs)
        sequencer.add_module_register('npts', modules=[dig])
        sequencer.add_module_register('dig_wait', modules=[dig])

        sync = sequencer.main
        awg_seqs = sequencer.get_module_builders(module_type='awg')
        dig_seqs = sequencer.get_module_builders(module_type='digitizer')
        all_seqs = awg_seqs + dig_seqs

        with sync.Main():
            with sync.SyncedModules():
                for awg_seq in awg_seqs:
                    awg_seq.start([1,2,3,4])
                    awg_seq.trigger([1,2,3,4])
                    awg_seq.wait(awg_seq['duration'])
                    awg_seq.stop([1,2,3,4])

                for dig_seq in dig_seqs:
                    dig_seq.start([1,2,3,4])
                    with dig_seq.Repeat(dig_seq['npts']):
                        dig_seq.trigger([1,2,3,4])
                        dig_seq.wait(dig_seq['dig_wait'])
                    dig_seq.stop([1,2,3,4])

        print(sequencer.describe())
        hvi_exec = sequencer.compile()

    Example SingleShot:

        sequencer = HviSequencer(hvi_system)

        sequencer.add_sync_register("start")
        sequencer.add_module_register("n_loops", 2, modules=[awg])
        sequencer.add_module_register('dig_wait', module_type='digitizer')

        sync = sequencer.main
        awg_seqs = sequencer.get_module_builders(module_type='awg')
        dig_seqs = sequencer.get_module_builders(module_type='digitizer')
        all_seqs = awg_seqs + dig_seqs

        with sync.Main():
            with sync.While(sync['start'] != 1):
                pass

            with sync.SyncedModules():
                for awg_seq in awg_seqs:
                    awg_seq.start()
                for dig_seq in dig_seqs:
                    dig_seq.start([1,2])
                    dig_seq.wait(150)

            with sync.Repeat(sync['n_loops']):
                with sync.SyncedModules():
                    for awg_seq in awg_seqs:
                        awg_seq.trigger()
                        # add 150 ns for AWG and digitizer to get ready for next trigger.
                        awg_seq.wait(wave_duration + 150)

                    for dig_seq in dig_seqs:
                        # add 290 ns delay to start acquiring when awg signal arrives at digitizer.
                        dig_seq.wait(290)
                        dig_seq.wait(dig_seq['dig_wait'])
                        dig_seq.trigger([1,2])

            with sync.SyncedModules():
                for seq in all_seqs:
                    seq.stop()

        hvi_exec = sequencer.compile()
    '''

    def __init__(self, system:HviSystem, alias:str='Sequencer'):
        print('Init HVI sequence')
        logging.info(f'Init HVI sequence')
        self.system = system
        self.kt_sequencer = Sequencer(alias, system.kt_system)
        logging.info(f'Sequence initialized')
        self.scopes = self.kt_sequencer.sync_sequence.scopes
        self.engine_registers = {engine.alias:{} for engine in self.system.engines}
        self.module_builders = {engine.alias:engine.create_sequence_builder(self, chr(ord('A')+i))
                                for i,engine in enumerate(self.system.engines)}
        self._main = SyncSequenceBuilder(self, self.kt_sequencer.sync_sequence, self.module_builders)
        self.errors = {}

    @property
    def main(self):
        return self._main

    def get_module_builders(self, module_aliases=None, modules=None, module_type=None):
        '''
        Gets or creates the local sequences for specified modules in this block.
        At most one of the keyword arguments `module_aliases`, `modules` and `module_type` may be set. If none
        of these arguments is set, then the a sequence will be returned for every module.
        Args:
            module_aliases (list of str): list of module aliases to return a local sequence for.
            modules (list of Keysight module): list of AWG and digitizer modules to return a local sequence for.
            module_type (str): type of the module to return a local sequence for.. 'awg' or 'digitizer'
        '''
        engines = self.system.get_engines(module_aliases=module_aliases, modules=modules, module_type=module_type)
        return tuple(self.module_builders[engine.alias] for engine in engines)

    def add_sync_register(self, alias, initial_value=None):
        '''
        Adds a register for use in synchronized sequence.
        Args:
            alias (str): name of the register
            initial_value (int): initial value. If None uses HVI register default (0).
        '''
        engine_alias = self.system._master_engine.alias

        return self._add_register(engine_alias, alias, initial_value)

    def _add_register(self, engine_alias, alias, initial_value=None):
        '''
        Adds a register to this engine for use in local sequences.
        '''
        registers = self.scopes[engine_alias].registers
        if alias.endswith(' #n'):
            base = alias[:-1]
            # count number of registers with same name
            n = reduce(lambda n,s:n+(s.startswith(base)), self.engine_registers[engine_alias], 0)
            alias = f'{base}{n+1}'
        kt_register = registers.add(alias, RegisterSize.SHORT) # @@@ test other sizes

        if initial_value is not None:
            kt_register.initial_value = initial_value
        register = Register(engine_alias, kt_register, initial_value)
        self.engine_registers[engine_alias][alias] = register
        return register

    def add_module_register(self, register_alias, initial_value=None, module_aliases=None, modules=None, module_type=None):
        '''
        Adds a register for use in local sequences.
        At most one of the keyword arguments `module_aliases`, `modules` and `module_type` may be set. If none
        of these arguments is set, then the register will be added to all modules.
        Args:
            register_alias (str): name of the register.
            initial_value (int): initial value. If None uses HVI register default (0).
            module_aliases (list of str): list of module aliases to add the register to.
            modules (list of Keysight module): list of AWG and digitizer modules to add the register to.
            module_type (str): type of the module to add the register to. 'awg' or 'digitizer'
        '''
        engines = self.system.get_engines(module_aliases=module_aliases, modules=modules, module_type=module_type)
        return ModuleRegister({engine: self._add_register(engine.alias, register_alias, initial_value) for engine in engines})

    def registers(self, engine_alias=None):
        if engine_alias is None:
            engine_alias = self.system._master_engine.alias
        return self.engine_registers[engine_alias]

    def _get_error_line(self, error_message):
        pattern = "'([0-9]+(?:[A-Z][0-9]+)?):"
        line_numbers = re.findall(pattern, error_message.description)
        return max(line_numbers) if len(line_numbers) > 0 else None

    def compile(self):
        try:
            print('Compiling HVI script')
            logging.info(f'Compiling HVI script')
            start = time.perf_counter()
            kt_hvi = self.kt_sequencer.compile()
            duration = time.perf_counter() - start
            status = kt_hvi.compile_status
#            logging.info(f'compiler: {status.to_string()}')
            logging.info(f'compiled in {status.elapsed_time.total_seconds():6.3f} s (actually: {duration:6.3f} s)')
            print(f'HVI Resources: {[str(s).rsplit(".",1)[-1] for s in status.sync_resources]}')
            for resource in status.sync_resources:
                logging.info(f'-- {resource}')
            return HviExec(kt_hvi, self)

        except CompilationFailed as exc:
            status = exc.compile_status
            logging.error(f'compiler: {status.to_string()}')
            logging.error(f'compilation failed ({status.elapsed_time.total_seconds():6.3f} s)')
            error_count = 0
            for message in status.messages:
                logging.error(message.description)
                line_number = self._get_error_line(message)
                if line_number is not None:
                    self.errors[line_number] = message
                else:
                    self.errors[f'#{error_count}'] = message
                error_count += 1
            for resource in status.sync_resources:
                logging.info(f'-- {resource}')
            logging.error(f"Compilation failed:\n" + self.describe(print_errors=True))
            raise

    def describe(self, **kwargs):
        result = 'Engines:\n'
        for engine in self.system.engines:
            result += f'    {engine.alias}\n'
        result += 'Registers:\n'
        for engine_alias, registers in self.engine_registers.items():
            for name, register in registers.items():
                result += f'    [{engine_alias}|{name}]:{register.initial_value}\n'
        result += 'Sequence:\n'
        result += SequencePrinter(**kwargs).print_sequence(self.main._main, self.errors)

        return result # @@@ TODO use object with __repr__ and __str__. IPython calls __repr__

class SequencePrinter:
    def __init__(self, print_line_numbers=True, print_start_delay=True, print_tail=False, print_errors=True):
        self.print_line_numbers = print_line_numbers
        self.print_start_delay = print_start_delay
        self.print_tail = print_tail
        self.print_errors = print_errors

    def get_line_prefix(self, line_number, start_delay, tail):
        result = ''
        if self.print_line_numbers:
            result += f'{line_number:4} '
        else:
            result += '    '
        if self.print_start_delay:
            result += f'{start_delay:+4}  ' if start_delay is not None else ' '*6
        if self.print_tail:
            result += f'({tail:4})  ' if tail is not None else ' '*8
        return result

    def get_line_prefix_empty(self):
        result = ''
        if self.print_line_numbers:
            result += '     '
        if self.print_start_delay:
            result += '      '
        if self.print_tail:
            result += '        '
        return result

    def _walk_statements(self, statements, indent):
        result = ''
        for statement in statements:
            text = statement.text
            prefix = self.get_line_prefix(statement.line, statement.start_delay, statement.timing_constraints.get_tail_ns())
            result += prefix + indent + text + '\n'
            if self.print_errors and statement.line in self.errors:
                error = self.errors[statement.line]
                result += '****  ' + error.description + '  ****\n'

            if isinstance(statement, BranchingStatement):
                sequences = statement.sequences
                for sequence in sequences:
                    if len(sequence.statements) == 0:
                        prefix = self.get_line_prefix_empty()
                        result += prefix + indent + '    pass\n'
                    else:
                        result += self._walk_statements(sequence.statements, indent + '    ')

            if isinstance(statement, SyncBlockStatement):
                sequences = statement.sequences
                for engine_name,sequence in sequences.items():
                    if len(sequence.statements) > 0:
                        prefix = self.get_line_prefix(sequence.line, None, sequence.tail)
                        result += prefix + indent + '| ' + engine_name + ':\n'
                        result += self._walk_statements(sequence.statements, indent + '|   ')
                        result += self.get_line_prefix_empty() + indent + '-'+'-'*29 + '\n'

        return result

    def print_sequence(self, sequence, errors):
        self.errors = errors
        return self._walk_statements(sequence.statements, '')