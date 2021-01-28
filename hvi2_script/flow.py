"""
@author: sdesnoo
"""
from dataclasses import dataclass, field
from typing import Dict, List, Union, Optional

from keysight_hvi import SyncSequence as HviSyncSequence
from keysight_hvi import Sequence as HviModuleSequence

from .instruction_timing import InstructionTiming


@dataclass
class Statement:
    line: str # line identification in builder (_1, A1, B3, ...)
    sequence: 'Sequence'
    start_delay: int
    text: str
    min_start_delay: int
    timing_constraints: InstructionTiming
    non_deterministic: Optional[str] = None

    @property
    def alias(self):
        return f'{self.line}:{self.text}'


@dataclass
class BranchingStatement(Statement):
    sequences: List['Sequence'] = field(default_factory=list)

    def append_sequence(self, sequence):
        self.sequences.append(sequence)


@dataclass
class SyncBlockStatement(Statement):
    sequences: Dict[str, 'Sequence'] = field(default_factory=dict)

    def append_sequence(self, engine_name, sequence):
        self.sequences[engine_name] = sequence


@dataclass
class Sequence:
    parent: 'Sequence'
    kt_sequence: Union[HviSyncSequence, HviModuleSequence]
    line: str
    entry_latency: int
    tail: int = 0 # minimum ns for start_delay of next instruction added to sequence or after this sequence
    duration: int = 0 # duration
    non_deterministics: List[str] = field(default_factory=list)
    statements: List[Statement] = field(default_factory=list)

    def __post_init__(self):
        self.tail = self.entry_latency

    @property
    def min_start_delay_next(self):
        return self.tail

    def append_statement(self, statement):
        start_delay = statement.start_delay
        if start_delay < self.tail:
            # don't step on the tail
            raise Exception(f'start delay of {start_delay} too short; minimum value:{self.tail}')
        self.tail = statement.timing_constraints.get_tail_ns()
        self.statements.append(statement)
        self.duration += start_delay

    def add_non_deterministic(self, non_deterministic):
        self.non_deterministics.append(non_deterministic)

    def total_duration(self):
        duration = 0
        non_deterministics = []
        for s in self.statements:
            duration += s.start_delay
            if s.non_deterministic is not None:
                non_deterministics.append(s.non_deterministic)
        return ' + '.join([str(duration)] + non_deterministics)

