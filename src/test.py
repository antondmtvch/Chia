import os
import time

for i in range(10):
    line = str(os.getpid()) + ' ' + str(i)
    if i == 2:
        line = str(os.getpid()) + ' ' + 'STARTING PHASE 2/4'
    print(line)
    time.sleep(0.5)

