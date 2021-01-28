import logging
logging.basicConfig(level=logging.INFO)

from pprint import pprint
import numpy as np

from sd1_utils import check_error

import keysightSD1 as SD1

from hvi2_script.system import HviSystem
from hvi2_script.sequencer import HviSequencer

# close objects still active since previous run (IPython)
try:
    for awg in awgs:
        awg.close()
    dig.close()
    hvi_exec.close()
except: pass



# ----- Open and configure AWG/Digitizer modules ------

simulated = False
module_options = ',simulate=true' if simulated else ''

slots = [3]
awgs = [None]*len(slots)
for i, slot in enumerate(slots):
    awgs[i] = SD1.SD_AOU()
    check_error(awgs[i].openWithOptions('M3202A', 1, slot, module_options), f'open awg{i}')

dig = SD1.SD_AIN()
check_error(dig.openWithOptions('M3102A', 1, 6, module_options), f'open dig')

n_points = 100

# load and enqueue waveforms
wave_data = np.concatenate([
        np.linspace(0, 1.0, 1000),
        np.linspace(1.0, 0.0, 1000),
#        [1.0]*2
        ])
wave_data = np.tile(wave_data, n_points)
wave_duration = len(wave_data)
wave = SD1.SD_Wave()
check_error(wave.newFromArrayDouble(SD1.SD_WaveformTypes.WAVE_ANALOG, wave_data))

for awg in awgs:
    check_error(awg.waveformFlush())
    check_error(awg.waveformLoad(wave, 1))
    for i in range(4):
        ch = i+1
        check_error(awg.AWGflush(ch))
        check_error(awg.channelAmplitude(ch, 1.0))
        check_error(awg.channelOffset(ch, 0.0))
        check_error(awg.channelWaveShape(ch, SD1.SD_Waveshapes.AOU_AWG))
        check_error(awg.AWGqueueConfig(ch, SD1.SD_QueueMode.CYCLIC))
        check_error(awg.AWGqueueWaveform(ch, 1, SD1.SD_TriggerModes.SWHVITRIG, 0, 1, 0))

mask = 0
n_samples = wave_duration // 2 #// 6 + 20
n_rep = 4
for c in range(0, 2):
    mask |= 1 << c
    ch = c + 1

    check_error(dig.channelInputConfig(ch, 2.0, SD1.AIN_Impedance.AIN_IMPEDANCE_50, SD1.AIN_Coupling.AIN_COUPLING_DC))
    check_error(dig.channelPrescalerConfig(ch, 0))
    check_error(dig.DAQconfig(ch, n_samples, n_rep, 0, SD1.SD_TriggerModes.SWHVITRIG))

# ------ HVI ------

hvi_system = HviSystem(chassis_number=1, simulated=simulated)
hvi_system.add_awgs(awgs)
hvi_system.add_digitizer(dig)

sequencer = HviSequencer(hvi_system)

start = sequencer.add_sync_register('start')
reg_duration = sequencer.add_module_register('duration', modules=awgs)
reg_npoints = sequencer.add_module_register('npts', modules=[dig])
reg_dig_wait = sequencer.add_module_register('dig_wait', modules=[dig])

sync = sequencer.main
awg_seqs = sequencer.get_module_builders(module_type='awg')
dig_seqs = sequencer.get_module_builders(module_type='digitizer')
all_seqs = awg_seqs + dig_seqs

with sync.Main():
    with sync.While(sync['start'] != 1):
        pass

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.start([1,2,3,4])
            awg_seq.trigger([1,2,3,4])
            awg_seq.wait(awg_seq['duration'])
            awg_seq.stop([1,2,3,4])

        for dig_seq in dig_seqs:
            dig_seq.start([1,2,3,4])
            with dig_seq.Repeat(dig_seq['npts']):
                dig_seq.trigger([1,2,3,4])
                dig_seq.wait(dig_seq['dig_wait'])
            dig_seq.stop([1,2,3,4])

print(sequencer.describe())

hvi_exec = sequencer.compile()
hvi_exec.load()

hvi_exec.set_register(reg_duration, wave_duration // 10)
hvi_exec.set_register(reg_npoints, n_points)
hvi_exec.set_register(reg_dig_wait, (wave_duration // n_points - 120)//10)
hvi_exec.set_register(start, 1)

pprint(hvi_exec.list_registers())

hvi_exec.start()

while hvi_exec.is_running():
    pass

pprint(hvi_exec.list_registers())
hvi_exec.close()


for awg in awgs:
    awg.close()
dig.close()
