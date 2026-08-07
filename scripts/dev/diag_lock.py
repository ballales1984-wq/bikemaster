
import ctypes

CreateFileW = ctypes.windll.kernel32.CreateFileW
GENERIC_READ = 0x80000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
OPEN_EXISTING = 3
files = [
    r'D:\BikeMaster\bike_analyzer\backend\settings.py',
    r'D:\BikeMaster\bike_analyzer\backend\security.py',
    r'D:\BikeMaster\pyproject.toml',
]
for f in files:
    h = CreateFileW(f, GENERIC_READ, FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE, None, OPEN_EXISTING, 0, None)
    if h == -1:
        err = ctypes.GetLastError()
        print(f, 'ERR', err, 'SHARING_VIOLATION' if err==32 else ('ACCESS_DENIED' if err==5 else 'other'))
    else:
        print(f, 'OK handle', h)
        ctypes.windll.kernel32.CloseHandle(h)

