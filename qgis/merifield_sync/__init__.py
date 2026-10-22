# SPDX-License-Identifier: GPL-3.0-or-later

def classFactory(iface):
    from .plugin import MerifieldSync
    return MerifieldSync(iface)
