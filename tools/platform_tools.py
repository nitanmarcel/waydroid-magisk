import platform


def _get_sse2_4():
    with open("/proc/cpuinfo") as f:
        if "sse4_2" not in f.read():
            return False
        return True

def get_arch():
    platform = platform.machine()
    if platform == "x86_64":
        return ("x86_64", 64) if get_sse2_4() else ("x86", 32)
    if platform in ["armv7l", "armv8l"]:
        return ("arm", 32)
    if platform == "aarch64":
        return ("arm64", 64)
    if platform == "i686":
        return ("x86_64", 64)