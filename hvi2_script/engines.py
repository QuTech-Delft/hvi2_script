"""
@author: sdesnoo
"""
import logging

class HviEngine:
    '''
    '''
    def __init__(self, alias, system, module, module_type):
        '''
        Args:
            alias (str): unique name of the engine
            system (Hvi2): HviSystem instance containing this engine
            module (AOU or AIN): AWG or Digitizer module
            module_type (str): 'awg' or 'digitizer'
        '''
        name = self._get_name(module)
        if alias is None:
            alias = name
        self.alias = alias
        self.name = name
        self.system = system
        self.module = module
        self.module_type= module_type
        # get instance of hvi engine of module
        exposed_engine_property = module.hvi.engines.main_engine
        self.kt_engine = self.system.kt_system.engines.add(exposed_engine_property, alias)
        self.extensions = {}
        logging.debug(f'engine: {self.kt_engine.name}')


    def create_sequence_builder(self, sequencer, module_id):
        ''' must be overridden '''
        raise NotImplementedError()

    def _get_action(self, action_name, alias=None):
        '''
        Retrieve action with specified `action_name`.
        '''
        if alias is None:
            alias = f'{self.alias}{action_name}'
        actions = self.module.hvi.actions
        action_id = getattr(actions, action_name)
        return self.kt_engine.actions.add(action_id, alias)

    def _get_event(self, event_name, alias=None):
        '''
        Retrieve event with specified `event_name`.
        '''
        if alias is None:
            alias = f'{self.alias}{event_name}'
        events = self.module.hvi.events
        event_id = getattr(events, event_name)
        return self.kt_engine.events.add(event_id, alias)

    def _get_name(self, module):
        ''' must be overridden '''
        raise NotImplementedError()

    @property
    def instruction_set(self):
        return self.module.hvi.instruction_set

    def load_fpga_symbols(self, bitstream):
        # # Get engine sandbox
        sandbox_name = "sandbox0"
        sandbox = self.kt_engine.fpga_sandboxes[sandbox_name]
        sandbox.load_from_k7z(bitstream)
        self.sandbox = sandbox

    def fpga_registers(self):
        return self.sandbox.fpga_registers

    def fpga_register(self, name):
        return self.sandbox.fpga_registers[name]

    def fpga_memory_map(self, name):
        return self.sandbox.fpga_memory_maps[name]

    def add_extension(self, name, extension):
        # add the instruction generators to a list. The builders will convert them to methods.
        self.extensions[name] = extension
