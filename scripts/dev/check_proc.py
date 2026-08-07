
import ctypes

kernel32 = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32
def elevated(pid):
    h = kernel32.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return "open-fail"
    token = ctypes.c_void_p()
    if not advapi32.OpenProcessToken(h, 0x8, ctypes.byref(token)):
        return 'token-fail'
    elevation = ctypes.c_ulong()
    retlen = ctypes.c_ulong()
    advapi32.GetTokenInformation(token, 20, ctypes.byref(elevation), 4, ctypes.byref(retlen))
    kernel32.CloseHandle(h)
    return bool(elevation.value)
for pid in [17124, 20648, 3336, 15188]:
    try:
        print(pid, elevated(pid))
    except Exception as e:
        print(pid, 'err', e)

