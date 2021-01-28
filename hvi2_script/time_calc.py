# -*- coding: utf-8 -*-
"""
Created on Tue Oct 27 19:41:54 2020

@author: sdesnoo
"""
from .flow import Statement, Sequence, BranchingStatement, SyncBlockStatement

class TimeCalc:
    def _find_in_sequence(self, statement:Statement, sequence:Sequence):
        for i, s in enumerate(sequence.statements):
            if s.line == statement.line:
                return i
        return None

    def get_time_between(self, start:Statement, end:Statement):
        if start.line > end.line:
            raise Exception(f'start {start.line} must be before end {end.line}')
        seq = end.sequence
        sequences = []
        index_start = None
        while index_start is None and seq is not None:
            sequences.append(seq)
            index_start = self._find_in_sequence(start, seq)
            seq = seq.parent
        if index_start is None:
            raise Exception(f'start {start.line} not found in path before {end.line}')
        total = 0
        non_deterministics = []
        sequences.reverse()
        for i,seq in enumerate(sequences):
            next_seq = sequences[i+1] if i+1 < len(sequences) else None
#            print(f'   seq: {seq.line}, {total}')
            for statement in seq.statements:
                if statement.line > start.line:
                    total += statement.start_delay
                if statement.line == end.line:
                    break
                if isinstance(statement, BranchingStatement):
                    if next_seq in statement.sequences:
                        break
                if isinstance(statement, SyncBlockStatement):
                    if next_seq in statement.sequences.values():
                        break
                if statement.line > start.line and statement.non_deterministic is not None:
                    non_deterministics.append(statement.non_deterministic)
#                print(f'     {statement.line}, {total}, {non_deterministics}')

        if statement.line != end.line:
            raise Exception('end not found')
        return total, non_deterministics


