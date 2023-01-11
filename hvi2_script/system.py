import logging
import time

from keysight_hvi import SystemDefinition, TriggerResourceId

from .awg_engine import HviAwgEngine
from .digitizer_engine import HviDigitizerEngine

class HviSystem:
    '''
    System definition and configuration used to build an HVI schedule with.

    Example:
        hvi_system = HviSystem(chassis_number=1)
        hvi_system.add_awgs(awgs)
        hvi_system.add_digitizer(dig)

        sequencer = HviSequencer(hvi_system)

    '''
    def __init__(self, alias='HVI', chassis_number=None, simulated=False):
        '''
        Creates HVI application builder and executer.
        Args:
            alias (str): alias for the application
            chassis_number (int or None): number of the chassis. Use auto-detect if None.
            simulated (bool): if True uses simulated HVI hardware.
        '''
        print('Init HVI System.... (takes a while)', flush=True)
        # add minimal sleep to print the message now.
        time.sleep(0.001)
        logging.info('Init HVI System')
        self.engines = []

        # create instance of hvi
        # all arbitrary names must be unique (different from one another) or an error will appear
        self.kt_system = SystemDefinition(alias)

        # Assign the defined PXI trigger resources (just allocate all...)
        self.kt_system.sync_resources = [
                TriggerResourceId.PXI_TRIGGER0,
                TriggerResourceId.PXI_TRIGGER1,
                TriggerResourceId.PXI_TRIGGER2,
                TriggerResourceId.PXI_TRIGGER3,
                TriggerResourceId.PXI_TRIGGER4,
                TriggerResourceId.PXI_TRIGGER5
                ]

        # Assign clock frequencies that are outside the set of the clock frequencies of each HVI engine
        # Use the code line below if you want the application to be in sync with the 10 MHz clock
#        self.hvi.synchronization.non_hvi_core_clocks = [10e6]

        chassis_coll = self.kt_system.chassis
        if simulated:
            chassis = chassis_coll.add_with_options(1, 'Simulate=True,DriverSetup=model=M9018B,NoDriver=True')
            logging.debug(f'chassis: {chassis.model} slots:{chassis.first_slot}..{chassis.last_slot}')
        elif chassis_number is None:
            # auto detects all available chassis to control the pxi trigger bus lines
            n = chassis_coll.add_auto_detect()
#            logging.debug(f'auto detect: {n} chassis')
            for i in range(n):
                chassis = chassis_coll[i+1]
                logging.debug(f'chassis: {chassis.model} slots:{chassis.first_slot}..{chassis.last_slot}')
        elif isinstance(chassis_number, int):
            chassis = chassis_coll.add(chassis_number)
            logging.debug(f'chassis: {chassis.model} slots:{chassis.first_slot}..{chassis.last_slot}')
        else:
            for n in chassis_number:
                chassis = chassis_coll.add(n)
                logging.debug(f'chassis: {chassis.model} slots:{chassis.first_slot}..{chassis.last_slot}')

        self._master_engine = None
        logging.info('HVI System initialized.')

    def _add_engine(self, engine):
        self.engines.append(engine)
        if len(self.engines) == 1:
            self._master_engine = engine

    def add_awgs(self, awgs):
        for awg in awgs:
            self.add_awg(awg)

    def add_awg(self, awg, alias=None):
        engine = HviAwgEngine(alias, self, awg)
        self._add_engine(engine)
        return engine

    def add_digitizer(self, dig, alias=None):
        engine = HviDigitizerEngine(alias, self, dig)
        self._add_engine(engine)
        return engine

    def add_digitizers(self, digitizers):
        for dig in digitizers:
            self.add_digitizer(dig)

    def get_engines(self, module_aliases=None, modules=None, module_type=None):
        if module_aliases is not None:
            engines = [engine for engine in self.engines if engine.alias in module_aliases]
        elif modules is not None:
            engines = [engine for engine in self.engines if engine.module in modules]
        elif module_type is not None:
            engines = [engine for engine in self.engines if engine.module_type in module_type]
        else:
            engines = self.engines
        return engines


