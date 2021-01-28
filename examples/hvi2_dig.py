import logging
logging.basicConfig(level=logging.INFO)

from pprint import pprint
import numpy as np
import matplotlib.pyplot as pt

from sd1_utils import check_error
from dig_utils import read_digitizer_data
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

simulated = False
module_options = ',simulate=true' if simulated else ''

slots = [3]
awgs = [None]*len(slots)
for i, slot in enumerate(slots):
    awgs[i] = SD1.SD_AOU()
    awgs[i].openWithOptions('M3202A', 1, slot, module_options)

dig = SD1.SD_AIN()
dig.openWithOptions('M3102A', 1, 6, module_options)
dig_channels = [1,2,3,4]

# load and enqueue waveforms
wave_data = np.concatenate([
        np.linspace(0, 1.0, 1000),
        np.linspace(1.0, 0.0, 1000),
        ])
wave_data = np.tile(wave_data, 1)
wave_duration = len(wave_data)
wave = SD1.SD_Wave()
check_error(wave.newFromArrayDoubleNP(SD1.SD_WaveformTypes.WAVE_ANALOG, wave_data))

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

for ch in dig_channels:
    c = ch - 1
    mask |= 1 << c

    check_error(dig.channelInputConfig(ch, 2.0, SD1.AIN_Impedance.AIN_IMPEDANCE_50, SD1.AIN_Coupling.AIN_COUPLING_DC))
    check_error(dig.channelPrescalerConfig(ch, 0))
    check_error(dig.DAQconfig(ch, n_samples, n_rep, 0, SD1.SD_TriggerModes.SWHVITRIG))

# ------ HVI ------

hvi_system = HviSystem(chassis_number=1, simulated=simulated)
hvi_system.add_awgs(awgs)
hvi_system.add_digitizer(dig)

sequencer = HviSequencer(hvi_system)

start = sequencer.add_sync_register('start')
n_loops = sequencer.add_sync_register('n_loops')
sequencer.add_module_register('dig_wait', 20)

sync = sequencer.main
awg_seqs = sequencer.get_module_builders(module_type='awg')
dig_seqs = sequencer.get_module_builders(module_type='digitizer')
all_seqs = awg_seqs + dig_seqs


with sync.Main():
    with sync.While(sync['start'] != 1):
        pass

    sync['start'] = 0

    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.start()
            awg_seq.wait(300)
        for dig_seq in dig_seqs:
            dig_seq.start(dig_channels)

    with sync.Repeat(sync['n_loops']):
        with sync.SyncedModules():
            for awg_seq in awg_seqs:
                awg_seq.trigger()
                awg_seq.wait(wave_duration + 300)
                awg_seq.wait(awg_seq['dig_wait'])

            for dig_seq in dig_seqs:
                dig_seq.wait(340)
                dig_seq.trigger(dig_channels)
                dig_seq.wait(dig_seq['dig_wait'])


    with sync.SyncedModules():
        for awg_seq in awg_seqs:
            awg_seq.stop()
        for dig_seq in dig_seqs:
            dig_seq.wait(300)
            dig_seq.stop(dig_channels)


print(sequencer.describe())

try:
    hvi_exec = sequencer.compile()
except:
    print(sequencer.describe())
    raise

hvi_exec.load()
pprint(hvi_exec.list_registers())

hvi_exec.set_register(n_loops, n_rep)
hvi_exec.set_register(start, 1)


hvi_exec.start()
hvi_exec.write_register(start, 1)

while hvi_exec.is_running():
    pass
pprint(hvi_exec.list_registers())


# ------- read digitizer data ------
loop_cnt = 0
tot_points = n_rep * n_samples
dataPoints = read_digitizer_data(dig, dig_channels, [tot_points]*4)

pt.figure()
pt.plot(dataPoints[0], 'r-', dataPoints[1], 'g-', dataPoints[2], 'b-', dataPoints[3], 'k-')
pt.show()


hvi_exec.close()
for awg in awgs:
    awg.close()
dig.close()
