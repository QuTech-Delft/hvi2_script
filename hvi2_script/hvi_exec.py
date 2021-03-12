from datetime import timedelta
from typing import Union

from keysight_hvi import Hvi

from .module_registers import ModuleRegister
from .registers import Register
#from .sequencer import HviSequencer

class HviExec:
    '''

    Example:
        sequencer = HviSequencer(hvi_system)

        start = sequencer.add_sync_register("start")
        n_loops = sequencer.add_module_register("n_loops", 2, modules=[awg])
        dig_wait = sequencer.add_module_register('dig_wait', module_type='digitizer')

        create_schedule(sequencer)

        hvi_exec = sequencer.compile()
        hvi_exec.load()
        pprint(hvi_exec.list_registers())

        hvi_exec.set_register(n_loops, 2)
        hvi_exec.set_register(dig_wait, 30)
        hvi_exec.set_register(start, 1)

        hvi_exec.start()

        while hvi_exec.is_running():
            pass

        hvi_exec.close()

    '''

    def __init__(self, hvi: Hvi, sequencer):
        self.kt_hvi = hvi
        self.sequencer = sequencer
        self._closed = False
        self._is_loaded = False

    def load(self):
        if not self._is_loaded:
            self.kt_hvi.load_to_hw()
            self._is_loaded = True

    def unload(self):
        if not self._is_loaded:
            return
        self.kt_hvi.release_hw()
        self._is_loaded = False

    def run(self):
        self.kt_hvi.run(timedelta(seconds=5))

    def start(self):
        self.kt_hvi.run(self.kt_hvi.no_wait)

    def stop(self):
        self.kt_hvi.stop()

    def is_running(self):
        return self.kt_hvi.is_running()

    def set_register(self, register: Union[Register, ModuleRegister], value):
        '''
        Sets the register value BEFORE start of the HVI schedule.
        '''
        if isinstance(register, ModuleRegister):
            for r in register.registers.values():
                self.set_register(r, value)
        else:
            rt_register = self.kt_hvi.sync_sequence.scopes[register.engine_name].registers[register.name]
            rt_register.initial_value = value

    def write_register(self, register: Union[Register, ModuleRegister], value):
        '''
        Writes `value` to `register` AFTER start of HVI schedule.
        '''
        if isinstance(register, ModuleRegister):
            for r in register.registers.values():
                self.write_register(r, value)
        else:
            rt_register = self.kt_hvi.sync_sequence.scopes[register.engine_name].registers[register.name]
            rt_register.write(value)

    def read_register(self, register: Register):
        rt_register = self.kt_hvi.sync_sequence.scopes[register.engine_name].registers[register.name]
        return rt_register.read()

    def read_multiple(self, module_register: ModuleRegister):
        '''
        Returns a dictionary with the value of the register per module.
        '''
        return {engine_alias: self.read_register(register) for engine_alias, register in module_register.registers.items()}

#    def read_one(self, module=None, module_alias=None):
#        '''
#        Returns the value of the register for specified module.
#        '''
#        if (module is None) == (module_alias is None):
#            raise Exception('specify module or module_alias')
#        for engine, register in self.registers.items():
#            if engine.module == module or engine.alias == module_alias:
#                return register.read()

    def list_registers(self):
        result = {}
        for engine_alias, registers in self.sequencer.engine_registers.items():
            for name, register in registers.items():
                result[f'{engine_alias}|{name}'] = self.read_register(register)
        return result

    def close(self):
        if self._is_loaded:
            self.unload()



