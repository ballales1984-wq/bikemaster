import os, time
for i in range(6):
    print('attempt', i, os.access('pyproject.toml', os.R_OK))
    time.sleep(2)
