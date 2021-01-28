import logging
logging.basicConfig(level=logging.DEBUG) # filename='logs/hvi.log',

from pprint import pprint
import time

from sd1_utils import check_error
from dig_utils import read_digitizer_data
import keysightSD1 as SD1

from hvi2_script.system import HviSystem
from hvi2_script.sequencer import HviSequencer

# close objects still active since previous run (IPython)
try:
    hvi_exec.close()
except: pass
try:
    awg.close()
except: pass

simulated = False
module_options = ',simulate=true' if simulated else ''

awg = SD1.SD_AOU()
check_error(awg.openWithOptions('M3202A', 1, 3, module_options))

check_error(awg.waveformFlush())
for i in range(4):
    ch = i+1
    check_error(awg.AWGflush(ch))
    check_error(awg.channelAmplitude(ch, 0.2))
    check_error(awg.channelOffset(ch, 0.0))
    check_error(awg.channelFrequency(ch, 1e8))
    check_error(awg.channelWaveShape(ch, SD1.SD_Waveshapes.AOU_SINUSOIDAL))
    check_error(awg.AWGstartMultiple(0b1111))

# ------ HVI ------

starttime = time.perf_counter()

hvi_system = HviSystem(chassis_number=1, simulated=simulated)
hvi_system.add_awg(awg)

sequencer = HviSequencer(hvi_system)

start = sequencer.add_sync_register("start")
n_loops = sequencer.add_module_register("n_loops", 2, modules=[awg])
sequencer.add_module_register("frequency", 2_000_000)

sync = sequencer.main
awg_seqs = sequencer.get_module_builders(module_type='awg')
dig_seqs = sequencer.get_module_builders(module_type='digitizer')
all_seqs = awg_seqs + dig_seqs

with sync.Main():
    with sync.While(sync['start'] != 1):
        pass

    with sync.Repeat(3):
        with sync.SyncedModules():
            for awg_seq in awg_seqs:
                awg_seq['frequency'] = 10e6
                awg_seq.set_frequency(4, awg_seq['frequency'])
                awg_seq.set_amplitude(4, 1.0)

                with awg_seq.Repeat(awg_seq['n_loops']):
                    awg_seq.set_frequency(4, awg_seq['frequency'])
                    awg_seq['frequency'] += 10e6
                    awg_seq.wait(50)

                awg_seq.set_amplitude(4, 0.0)

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.set_amplitude(4, 0.0)

print(sequencer.describe())

hvi_exec = sequencer.compile()
hvi_exec.load()
pprint(hvi_exec.list_registers())

hvi_exec.set_register(n_loops, 2)
hvi_exec.set_register(start, 1)

hvi_exec.start()


while hvi_exec.is_running():
    pass

print(f'after running:')
pprint(hvi_exec.list_registers())

hvi_exec.close()
awg.close()
