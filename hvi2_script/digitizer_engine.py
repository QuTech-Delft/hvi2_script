"""
@author: sdesnoo
"""

from .module_builder import ModuleSequenceBuilder
from .engines import HviEngine
from .instruction_timing import InstructionTiming


class HviDigitizerEngine(HviEngine):
    '''
    '''
    def __init__(self, alias, system, dig):
        super().__init__(alias, system, dig, 'digitizer')
        # register commonly used actions: daq_start, daq_trigger, daq_stop
        self.start_actions = [self._get_action(f'daq{i}_start') for i in range(1,5)]
        self.trigger_actions = [self._get_action(f'daq{i}_trigger') for i in range(1,5)]
        self.stop_actions = [self._get_action(f'daq{i}_stop') for i in range(1,5)]

    def _get_name(self, dig):
        return f'DIG{dig.getChassis()}-{dig.getSlot()}'

    def create_sequence_builder(self, sequencer, module_id):
        return DigitizerSequenceBuilder(sequencer, self, module_id)


class DigitizerSequenceBuilder(ModuleSequenceBuilder):
    def __init__(self, sequencer, engine, module_id):
        super().__init__(engine, module_id, sequencer)

    def start(self, channels=[1,2,3,4]):
        '''
        Adds daq_start action to the sequence.
        Args:
            channels (list of int): channels to start.
        '''
        actions = [self.engine.start_actions[i-1] for i in channels]
        self._add_actions(f'daq_start {channels}', actions,
                          InstructionTiming(1, 120))
        return self._current_statement

    def trigger(self, channels=[1,2,3,4]):
        '''
        Adds daq_trigger action to the sequence.
        Args:
            channels (list of int): channels to trigger.
        '''
        actions = [self.engine.trigger_actions[i-1] for i in channels]
        self._add_actions(f'daq_trigger {channels}', actions,
                          InstructionTiming(1, 330))
        return self._current_statement

    def stop(self, channels=[1,2,3,4]):
        '''
        Adds daq_stop action to the sequence.
        Args:
            channels (list of int): channels to stop.
        '''
        actions = [self.engine.stop_actions[i-1] for i in channels]
        self._add_actions(f'daq_stop {channels}', actions,
                          InstructionTiming(1, 1))
        return self._current_statement

    def daq_config(self, channel, points_per_cycle, cycles, trigger_delay=0, trigger_mode=1):
        '''
        Adds daq_config instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'daq_config({channel}, {points_per_cycle}, {cycles}, {trigger_delay}, {trigger_mode})',
                'daq_config',
                InstructionTiming(2, execution_time=80),
                params={'channel':channel,
                        'daq_points_per_cycle':points_per_cycle,
                        'cycles':cycles,
                        'trigger_delay':trigger_delay,
                        'trigger_mode':trigger_mode}
                )
        return self._current_statement

    def prescaler_config(self, channel, prescaler):
        '''
        Adds prescaler_config instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'prescaler_config({channel}, {prescaler})',
                'channel_prescaler_config',
                InstructionTiming(1, execution_time=30),
                params={'channel':channel, 'prescaler':prescaler}
                )
        return self._current_statement

    def channel_trigger_config(self, channel, analog_trigger_mode, threshold):
        '''
        Adds channel_trigger_config instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'channel_trigger_config({channel}, {analog_trigger_mode}, {threshold})',
                'channel_trigger_config',
                InstructionTiming(1, execution_time=30),
                params={'channel':channel,
                        'analog_trigger_mode':analog_trigger_mode,
                        'threshold':threshold}
                )
        return self._current_statement

    def daq_analog_trigger_config(self, channel, analog_trigger_mask):
        '''
        Adds daq_analog_trigger_config instruction to the sequence.
        '''
        self._add_engine_instruction(
                f'daq_analog_trigger_config({channel}, {analog_trigger_mask})',
                'daq_analog_trigger_config',
                InstructionTiming(1, execution_time=330),
                params={'channel':channel, 'analog_trigger_mask':analog_trigger_mask}
                )
        return self._current_statement


