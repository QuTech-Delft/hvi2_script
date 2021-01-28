import logging
logging.basicConfig(level=logging.INFO) # filename='logs/hvi.log',

import numpy as np

from sd1_utils import check_error
import keysightSD1 as SD1

from hvi2_script.system import HviSystem
from hvi2_script.sequencer import HviSequencer

try:
    awg.close()
except: pass
try:
    hvi_exec.close()
except: pass


module_options = ''

awg = SD1.SD_AOU()
awg.openWithOptions('M3202A', 1, 3, module_options)

# load and enqueue waveforms
wave_data = np.concatenate([
        np.zeros(100),
        np.ones(1900),
        np.zeros(100),
        ])
wave_duration = len(wave_data)
wave = SD1.SD_Wave()
check_error(wave.newFromArrayDouble(SD1.SD_WaveformTypes.WAVE_ANALOG, wave_data))

check_error(awg.waveformFlush())
check_error(awg.waveformLoad(wave, 1))

# ------ HVI ------

hvi_system = HviSystem(chassis_number=1)

hvi_system.add_awg(awg)

sequencer = HviSequencer(hvi_system)

sequencer.add_module_register("wave_duration", 20*wave_duration // 10)

awg_seqs = sequencer.get_module_builders(module_type='awg')

sync = sequencer.main
with sync.Main():

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.start()

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.trigger()
            awg_seq.wait(awg_seq['wave_duration'])

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.stop()

#print(sequencer.describe())

try:
    hvi_exec = sequencer.compile()
except:
    print(sequencer.describe())
    raise

queue_before_load = False

if queue_before_load:
    for i in range(4):
        ch = i+1
        check_error(awg.AWGflush(ch))
        check_error(awg.channelAmplitude(ch, 1.0))
        check_error(awg.channelWaveShape(ch, SD1.SD_Waveshapes.AOU_AWG))
        check_error(awg.AWGqueueConfig(ch, SD1.SD_QueueMode.CYCLIC))
        check_error(awg.AWGqueueWaveform(ch, 1, SD1.SD_TriggerModes.SWHVITRIG, 0, 1, 2))

hvi_exec.load()

if not queue_before_load:
    for i in range(4):
        ch = i+1
        check_error(awg.AWGflush(ch))
        check_error(awg.channelAmplitude(ch, 1.0))
        check_error(awg.channelWaveShape(ch, SD1.SD_Waveshapes.AOU_AWG))
        check_error(awg.AWGqueueConfig(ch, SD1.SD_QueueMode.CYCLIC))
        # FAILS:
        #check_error(awg.AWGqueueWaveform(ch, 1, SD1.SD_TriggerModes.SWHVITRIG, 0, 1, 2))
        # WORKS:
        check_error(awg.AWGqueueWaveform(ch, 1, SD1.SD_TriggerModes.SWHVITRIG_CYCLE, 0, 1, 2))


hvi_exec.start()
while hvi_exec.is_running():
    pass


hvi_exec.close()
awg.close()
