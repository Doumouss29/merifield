"""Small, capability-checked adapter to the installed QFieldSync plugin.

The application uses the installed plugin, without bundling or replacing it.
Upstream interfaces checked against QFieldSync c8abedb9317607f5fd040742ba4071e592dff543.
"""
# SPDX-License-Identifier: GPL-3.0-or-later
from qgis.utils import plugins
from .core import normalize_server


class SyncBridge:
    def instance(self):
        plugin = plugins.get('qfieldsync')
        if plugin is None:
            raise ValueError('Installer et activer QFieldSync dans Extensions → Installer/Gérer les extensions, puis réessayer.')
        return plugin

    def call(self, method):
        callback = getattr(self.instance(), method, None)
        if not callable(callback):
            raise ValueError('Cette version de QFieldSync ne propose pas cette fonction. Mettre QFieldSync à jour.')
        callback()

    def cloud(self, target):
        target = normalize_server(target)
        plugin = self.instance()
        manager = getattr(plugin, 'network_manager', None)
        if manager is None or not callable(getattr(manager, 'set_url', None)):
            raise ValueError('Mettre QFieldSync à jour : gestion des serveurs indisponible.')
        current = normalize_server(manager.url or 'https://app.qfield.cloud/')
        if current != target:
            # Never redirect an authenticated client (including persisted auth)
            # to another host. The QFieldSync login screen owns account changes.
            prefs = getattr(manager, 'preferences', None)
            authcfg = prefs.value('qfieldCloudAuthcfg') if prefs else None
            if manager.is_authenticated() or authcfg or getattr(manager, 'is_login_active', False):
                self.call('show_cloud_overview_dialog')
                raise ValueError('Un compte QFieldSync est associé à un autre serveur. Déconnecter ce compte dans la fenêtre QFieldSync, puis réessayer la destination choisie. Aucun identifiant n’a été transféré.')
            manager.set_url(target)
        self.call('show_cloud_overview_dialog')
