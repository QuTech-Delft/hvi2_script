"""
@author: sdesnoo
"""
from .module_builder import ModuleSequenceBuilder
from .engines import HviEngine
from .instruction_timing import InstructionTiming
from .events import Event

class HviAwgEngine(HviEngine):
    '''
    '''
    def __init__(self, alias, system, awg):
        super().__init__(alias, system, awg, 'awg')
        # register commonly used actions: awg_start, awg_trigger, awg_stop
        self.start_actions = [self._get_action(f'awg{i}_start') for i in range(1,5)]
        self.trigger_actions = [self._get_action(f'awg{i}_trigger') for i in range(1,5)]
        self.stop_actions = [self._get_action(f'awg{i}_stop') for i in range(1,5)]
        self.fpga_events = [Event(self.alias, self._get_event(f'fpga_user_{i}')) for i in range(8)]
        self.queue_flush_actions = [self._get_action(f'awg{i}_queue_flush') for i in range(1,5)]
        self.reset_phase_actions = [self._get_action(f'ch{i}_reset_phase') for i in range(1,5)]

    def _get_name(self, awg):
        return f'AWG{awg.getChassis()}-{awg.getSlot()}'

    def create_sequence_builder(self, sequencer, module_id):
        return AwgSequenceBuilder(sequencer, self, module_id)


class AwgSequenceBuilder(ModuleSequenceBuilder):
    def __init__(self, sequencer, engine, module_id):
        super().__init__(engine, module_id, sequencer)

    def start(self, channels=[1,2,3,4]):
        '''
        Adds start action to the sequence.
        Args:
            channels (list of int): channels to start.
        '''
        actions = [self.engine.start_actions[i-1] for i in channels]
        self._add_actions(f'awg_start {channels}', actions,
                          InstructionTiming(1, 122))
        return self._current_statement

    def trigger(self, channels=[1,2,3,4]):
        '''
        Adds awg_trigger action to the sequence.
        Args:
            channels (list of int): channels to trigger.
        '''
        actions = [self.engine.trigger_actions[i-1] for i in channels]
        self._add_actions(f'awg_trigger {channels}', actions,
                          InstructionTiming(1, 112))
        return self._current_statement

    def stop(self, channels=[1,2,3,4]):
        '''
        Adds awg_stop action to the sequence.
        Args:
            channels (list of int): channels to stop.
        '''
        actions = [self.engine.stop_actions[i-1] for i in channels]
        self._add_actions(f'awg_stop {channels}', actions,
                          InstructionTiming(1, 120))
        return self._current_statement

    def reset_phase(self, channels=[1,2,3,4]):
        actions = [self.engine.reset_phase_actions[i-1] for i in channels]
        self._add_actions(f'reset_phase {channels}', actions,
                          InstructionTiming(1, 120))
        return self._current_statement

    def queue_flush(self, channels=[1,2,3,4]):
        '''
        Adds awg_flush action to the sequence.
        Args:
            channels (list of int): channels to flush.
        '''
        actions = [self.engine.queue_flush_actions[i-1] for i in channels]
        self._add_actions(f'awg_flush {channels}', actions,
                          InstructionTiming(1, 119))
        return self._current_statement

    def queue(self, channel, waveform_number, cycles=1, wave_start_delay=0, prescaler=0, trigger_mode=1):
        '''
        Adds queue_waveform instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'queue_waveform({channel}, {waveform_number}, {cycles}, {wave_start_delay}, {prescaler}, {trigger_mode})',
                'queue_waveform',
                InstructionTiming(2, execution_time=1550),
                params={'channel':channel,
                        'waveform_number':waveform_number,
                        'cycles':cycles,
                        'start_delay':wave_start_delay,
                        'prescaler':prescaler,
                        'trigger_mode':trigger_mode}
                )
        return self._current_statement

    def set_amplitude(self, channel, value):
        '''
        Adds set_amplitude instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'set_amplitude({channel}, {value})',
                'set_amplitude',
                InstructionTiming(1, execution_time=115),
                params={'channel':channel,
                        'value':value}
                )
        return self._current_statement

    def set_offset(self, channel, value):
        '''
        Adds set_offset instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'set_offset({channel}, {value})',
                'set_offset',
                InstructionTiming(1, execution_time=115),
                params={'channel':channel, 'value':value}
                )
        return self._current_statement

    def set_frequency(self, channel, value):
        '''
        Adds set_frequency instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'set_frequency({channel}, {value})',
                'set_frequency',
                InstructionTiming(1, execution_time=172),
                params={'channel':channel, 'value':value}
                )
        return self._current_statement

    def set_waveshape(self, channel, value):
        '''
        Adds set_waveshape instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'set_waveshape({channel}, {value})',
                'set_waveshape',
                InstructionTiming(1, execution_time=132),
                params={'channel':channel, 'value':value}
                )
        return self._current_statement

    def set_phase(self, channel, value):
        '''
        Adds set_phase instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'set_phase({channel}, {value})',
                'set_phase',
                InstructionTiming(1, execution_time=155),
                params={'channel':channel, 'value':value}
                )
        return self._current_statement

    def modulation_angle_config(self, channel, modulation_type, deviation_gain):
        '''
        Adds modulation_angle_config instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'modulation_angle_config({channel}, {modulation_type}, {deviation_gain})',
                'modulation_angle_config',
                InstructionTiming(1, execution_time=204),
                params={'channel':channel,
                        'modulation_type':modulation_type,
                        'deviation_gain':deviation_gain}
                )
        return self._current_statement

    def modulation_amplitude_config(self, channel, modulation_type, deviation_gain):
        '''
        Adds modulation_amplitude_config instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'modulation_amplitude_config({channel}, {modulation_type}, {deviation_gain})',
                'modulation_amplitude_config',
                InstructionTiming(1, execution_time=106),
                params={'channel':channel,
                        'modulation_type':modulation_type,
                        'deviation_gain':deviation_gain}
                )
        return self._current_statement
