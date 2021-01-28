# -*- coding: utf-8 -*-
"""
Created on Thu Oct 22 18:32:08 2020

@author: sdesnoo
"""
import numpy as np

from sd1_utils import check_error

def read_digitizer_data(dig, dig_channels, npoints):
    READ_TIMEOUT = 1000

    numReadPoints = []
    dataPoints = []

    for c in range(4):
        numReadPoints.append(0)
        dataPoints.append(np.empty(0, dtype=np.short))

#    print()
#    print("Reading data...")

    readDone = False
    cnt = 0
    while readDone == False:

        if (cnt >= 8):
            break

        readDone = True
        for ch in dig_channels:
            c = ch - 1
            npts = dig.DAQcounterRead(ch)
            if npts <= 0:
                print(f'channel {ch} counter {npts} {numReadPoints[c]}')
                cnt += 1
            else:
                readPoints = dig.DAQread(ch, min(npoints[c], npts), READ_TIMEOUT)
                check_error(readPoints)

                if type(readPoints) is int or readPoints.size == 0:
                    cnt += 1
                    print(f'channel {ch} counter {npts} {numReadPoints[c]} {readPoints}')
                else:
                    dataPoints[c] = np.append(dataPoints[c], readPoints)
                    numReadPoints[c] += readPoints.size
#                    print(f'channel {ch} counter {npts} read {readPoints.size} ({numReadPoints[c]}) ({cnt})')

            readDone = readDone and (numReadPoints[c] >= npoints[c])

    return dataPoints