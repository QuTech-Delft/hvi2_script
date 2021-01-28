import logging
logging.basicConfig(level=logging.INFO) # filename='logs/hvi.log',

from pprint import pprint
import time
import numpy as np

from sd1_utils import check_error
import keysightSD1 as SD1

from hvi2_script.system import HviSystem
from hvi2_script.sequencer import HviSequencer

try:
    for awg in awgs:
        awg.close()
except: pass
try:
    hvi_exec.close()
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

hvi_system = HviSystem(chassis_number=1, simulated=simulated)

hvi_system.add_awgs(awgs)

sequencer = HviSequencer(hvi_system)

start = sequencer.add_sync_register("start", 0)
stop = sequencer.add_sync_register("stop", 0)
n_loops = sequencer.add_module_register("n_loops", 2)#, modules=[awg1,awg2])
sequencer.add_module_register("wave_duration", 20*wave_duration // 10)
sequencer.add_module_register('state', 0)

awg_seqs = sequencer.get_module_builders(module_type='awg')

sync = sequencer.main
with sync.Main():

    # note "and" is a bitwise and (&)
    with sync.While((sync['start'] == 0) & (sync['stop'] == 0)):
        pass

    with sync.While(~(sync['start'] == 0)):
        sync['start'] = 0

        with sync.SyncedModules():
            for awg_seq in awg_seqs:
                awg_seq.start()
                awg_seq['state'] = 1

        with sync.SyncedModules() as sm1:
            for awg_seq in awg_seqs:
                awg_seq['state'] = 2
                with awg_seq.Repeat(awg_seq['n_loops']) as rep2:
                    awg_seq.trigger()
                    awg_seq['state'] = awg_seq['n_loops'] + 10
                    awg_seq.wait(awg_seq['wave_duration'])
                awg_seq['state'] = 3

        with sync.SyncedModules():
            for awg_seq in awg_seqs:
                awg_seq.stop()
                awg_seq['state'] = 4

print(sequencer.describe())


try:
    hvi_exec = sequencer.compile()
except:
    #
    print(sequencer.describe())
    raise

hvi_exec.load()

hvi_exec.start()
time.sleep(0.1)
print(hvi_exec.is_running())
hvi_exec.write_register(start, 1)
hvi_exec.write_register(stop, 1)

time.sleep(0.1)
while hvi_exec.is_running():
    pass

pprint(hvi_exec.list_registers())

hvi_exec.close()
for awg in awgs:
    awg.close()

