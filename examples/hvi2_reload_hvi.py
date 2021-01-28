import logging
logging.basicConfig(level=logging.INFO) # filename='logs/hvi.log',

from pprint import pprint
import time
import numpy as np

from sd1_utils import check_error

import keysightSD1 as SD1

from hvi2_script.system import HviSystem
from hvi2_script.sequencer import HviSequencer

# close objects still active since previous run (IPython)
try:
    hvi_exec.close()
    hvi_exec2.close()
except: pass
try:
    for awg in awgs:
        awg.close()
except: pass


simulated = False
module_options = ',simulate=true' if simulated else ''

slots = [3]
awgs = []
for slot in slots:
    awg = SD1.SD_AOU()
    awg.openWithOptions('M3202A', 1, slot, module_options)
    awgs.append(awg)

# load and enqueue waveforms
wave_data = np.concatenate([
        np.zeros(10),
        0.5*np.ones(190),
        np.zeros(100),
        np.ones(1400),
        np.zeros(100),
        0.8*np.ones(190),
        np.zeros(10),
        ])
wave_duration = len(wave_data)
wave = SD1.SD_Wave()
check_error(wave.newFromArrayDouble(SD1.SD_WaveformTypes.WAVE_ANALOG, wave_data))

check_error(awg.waveformFlush())
check_error(awg.waveformLoad(wave, 1))
for i in range(4):
    ch = i+1
    check_error(awg.AWGflush(ch))
    check_error(awg.channelAmplitude(ch, 1.0))
    check_error(awg.channelWaveShape(ch, SD1.SD_Waveshapes.AOU_AWG))
    check_error(awg.AWGqueueConfig(ch, SD1.SD_QueueMode.CYCLIC))
    check_error(awg.AWGqueueWaveform(ch, 1, SD1.SD_TriggerModes.SWHVITRIG, 0, 1, 2))

time.sleep(0.5)

# ------ HVI ------

start = time.perf_counter()
hvi_system = HviSystem(chassis_number=1, simulated=simulated)

hvi_system.add_awgs(awgs)

end = time.perf_counter()
t_sys = (end-start)*1000
print(f'system:{t_sys:5.2f} ms')

sequencer = HviSequencer(hvi_system)

sequencer.add_module_register("state", 0)
n_loops = sequencer.add_module_register("n_loops", 2, modules=awgs)
sequencer.add_module_register("wave_duration", 20*wave_duration // 10)
sequencer.add_module_register("counter")

awg_seqs = sequencer.get_module_builders(modules=awgs)

sync = sequencer.main
with sync.Main():
    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.start()
            awg_seq['state'] = 1

    with sync.Repeat(2):
        with sync.SyncedModules():
            for awg_seq in awg_seqs:
                awg_seq['state'] = 2
                with awg_seq.Repeat(awg_seq['n_loops']):
                    awg_seq.trigger()
                    awg_seq.wait(500)
                    awg_seq['counter'] += 1

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq['state'] = 3
            awg_seq.stop()


print(sequencer.describe())

## 2
sequencer2 = HviSequencer(hvi_system)

n_loops2 = sequencer2.add_module_register("n_loops", 5, modules=awgs)
sequencer2.add_module_register("counter")

awg_seqs = sequencer2.get_module_builders(modules=awgs)

sync = sequencer2.main
with sync.Main():
    with sync.Repeat(3):
        with sync.SyncedModules():
            for awg_seq in awg_seqs:
                awg_seq.start()
                with awg_seq.Repeat(awg_seq['n_loops']):
                    awg_seq.trigger()
                    awg_seq.wait(1500)
                    awg_seq['counter'] += 1
                awg_seq.stop()

print(sequencer2.describe())
##

try:
    start = time.perf_counter()
    hvi_exec = sequencer.compile()
    end = time.perf_counter()
    t_comp = (end-start)*1000
    print(f'compile:{t_comp:5.2f} ms')
    time.sleep(0.5)
except:
    print(sequencer.describe())
    raise

try:
    start = time.perf_counter()
    hvi_exec2 = sequencer2.compile()
    end = time.perf_counter()
    t_comp = (end-start)*1000
    print(f'compile:{t_comp:5.2f} ms')
    time.sleep(0.5)
except:
    print(sequencer2.describe())
    raise

##
def execute(hvi_exec, msg):
    start = time.perf_counter()
    hvi_exec.load()
    end = time.perf_counter()
    t_load = (end-start)*1000
#    pprint(hvi_exec.list_registers())
    start = time.perf_counter()
    hvi_exec.start()
    end = time.perf_counter()
    t_start = (end-start)*1000

    while hvi_exec.is_running():
        pass

#    pprint(hvi_exec.list_registers())
    start = time.perf_counter()
    hvi_exec.unload()
    end = time.perf_counter()
    t_unload = (end-start)*1000
    print(f'{msg}: load:{t_load:5.1f} ms, start:{t_start:4.1f} ms, unload:{t_unload:4.1f} ms') # @@@ log in HviExec
    time.sleep(0.5)

time.sleep(0.5)
for i in range(4):
    execute(hvi_exec, f'{i}-a')
    execute(hvi_exec2, f'{i}-b')


hvi_exec.close()
hvi_exec2.close()
for awg in awgs:
    awg.close()


