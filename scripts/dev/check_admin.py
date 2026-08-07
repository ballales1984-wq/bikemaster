
import ctypes

# Check if process is elevated
try:
    import ctypes.wintypes as wt
    # OpenProcessToken
    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32
    token = wt.HANDLE()
    kernel32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x8, ctypes.byref(token))  # TOKEN_QUERY
    # GetTokenInformation TokenElevation
    elevation = ctypes.c_ulong()
    retlen = ctypes.c_ulong()
    advapi32.GetTokenInformation(token, 20, ctypes.byref(elevation), 4, ctypes.byref(retlen))
    print('Elevated:', bool(elevation.value))
except Exception as e:
    print('err', e)

