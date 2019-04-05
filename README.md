# nimi-basics
Provides an abstraction layer around some of nimi python by National Instruments

Not affiliated with National Instruments in any way

Not really setup as a proper module yet

So far there are only two items and they were built with my specific situation
in mind

1. resistance_manager.py allows you to specify Ohms on a channel
2. switch_manager.py provides functionality so ease use of a switch matrix

```python
# ResistanceManager usage
from resistance_manager import ResistanceManager
rm = ResistanceManager(device="PXI1Slot3", channel=0, topo="2722/Independent")
rm.setResistance(1000) # 1000 Ohms

# SwitchManager usage example
from switch_manager import SwitchManager
sm = SwitchManager(device="PXI1Slot4", topo="2531/1-Wire 8x64 Matrix")
cols, rows = sm.getChannels()
print(cols)
print(rows)
print(sm.getConnections(row_slice=(2, 3), col_slice=(60, None)))
print("----")
# sm.clearRow('r7')
sm.clearCol('c62')

# connect 'r7'->'c38'...'r7'->'c63'
for col in cols[38:]:
    sm.connect('r7',col)

sm.clearRow('r7')

print(sm.getConnections())

```
