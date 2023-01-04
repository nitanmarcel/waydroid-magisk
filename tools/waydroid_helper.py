import dbus


class WaydroidHelper(object):
    def __init__(self):
        self.bus = dbus.SystemBus()
