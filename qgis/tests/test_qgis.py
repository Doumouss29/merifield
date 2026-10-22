"""Run with QGIS Python: QT_QPA_PLATFORM=offscreen /usr/bin/python3 ..."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).parents[1]))
from qgis.core import QgsApplication, QgsField, QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsFeature
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import QAction, QMainWindow
from qgis.utils import plugins
from merifield_sync.core import configure_signatures, signature_names, normalize_server, diagnose
from merifield_sync.bridge import SyncBridge
from merifield_sync.plugin import MerifieldSync

app = QgsApplication([], False)
app.initQgis()


class SignatureTests(unittest.TestCase):
    def tearDown(self):
        QgsProject.instance().clear()

    def test_create_two_fields_roundtrip_and_keep_existing_value(self):
        layer = QgsVectorLayer('Point?crs=EPSG:4326&field=nom:string', 'Test', 'memory')
        QgsProject.instance().addMapLayer(layer)
        self.assertEqual(['signature_demandeur', 'signature_temoin'], configure_signatures(layer, ['signature_demandeur', 'signature_temoin']))
        self.assertEqual(['signature_demandeur', 'signature_temoin'], signature_names(layer))
        for field in signature_names(layer):
            setup = layer.editorWidgetSetup(layer.fields().indexFromName(field))
            self.assertEqual('ExternalResource', setup.type())
            self.assertEqual(1, setup.config()['RelativeStorage'])
        # Applying configuration does not open or commit a user's edit session.
        layer.startEditing()
        configure_signatures(layer, ['signature_demandeur'])
        self.assertTrue(layer.isEditable())
        layer.rollBack()

    def test_geopackage_schema_and_existing_image_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = QgsVectorLayer('Point?crs=EPSG:4326&field=signature_demandeur:string', 'Source', 'memory')
            feature = QgsFeature(source.fields())
            feature['signature_demandeur'] = 'DCIM/existing.png'
            source.dataProvider().addFeatures([feature])
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GPKG'
            options.layerName = 'signatures'
            result = QgsVectorFileWriter.writeAsVectorFormatV3(source, str(Path(tmp) / 'test.gpkg'), QgsProject.instance().transformContext(), options)
            self.assertEqual(QgsVectorFileWriter.NoError, result[0])
            layer = QgsVectorLayer(str(Path(tmp) / 'test.gpkg') + '|layername=signatures', 'Terrain', 'ogr')
            self.assertTrue(layer.isValid())
            configure_signatures(layer, ['signature_demandeur', 'signature_temoin'])
            self.assertFalse(layer.isEditable())
            self.assertGreaterEqual(layer.fields().indexFromName('signature_temoin'), 0)
            self.assertEqual('DCIM/existing.png', next(layer.getFeatures())['signature_demandeur'])
            reopened = QgsVectorLayer(str(Path(tmp) / 'test.gpkg') + '|layername=signatures', 'Terrain', 'ogr')
            self.assertGreaterEqual(reopened.fields().indexFromName('signature_temoin'), 0)

    def test_never_commits_user_edits_for_new_columns(self):
        layer = QgsVectorLayer('Point?field=nom:string', 'Test', 'memory')
        layer.startEditing()
        with self.assertRaisesRegex(ValueError, 'modifications'):
            configure_signatures(layer, ['signature_demandeur'])
        self.assertTrue(layer.isEditable())
        self.assertEqual(-1, layer.fields().indexFromName('signature_demandeur'))
        layer.rollBack()

    def test_non_text_and_bad_names_rejected_without_schema_change(self):
        layer = QgsVectorLayer('Point?field=signature_count:integer', 'Test', 'memory')
        for names in [['signature_count'], ['signature_new', 'bad/name']]:
            with self.assertRaises(ValueError):
                configure_signatures(layer, names)
        self.assertEqual(-1, layer.fields().indexFromName('signature_new'))

    def test_demo_project_is_valid_and_signature_settings_persist(self):
        path = Path(__file__).parents[1] / 'merifield_sync/example/Test_signatures.qgs'
        project = QgsProject()
        self.assertTrue(project.read(str(path)))
        self.assertEqual(1, len(project.mapLayers()))
        layer = next(iter(project.mapLayers().values()))
        self.assertTrue(layer.isValid())
        self.assertEqual(1, layer.featureCount())
        for name in ['signature_demandeur', 'signature_temoin']:
            self.assertGreaterEqual(layer.fields().indexFromName(name), 0)
            self.assertEqual('ExternalResource', layer.editorWidgetSetup(layer.fields().indexFromName(name)).type())
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(project.write(str(Path(tmp) / 'roundtrip.qgs')))
            again = QgsProject()
            self.assertTrue(again.read(str(Path(tmp) / 'roundtrip.qgs')))
            l2 = next(iter(again.mapLayers().values()))
            self.assertTrue(l2.isValid())
            self.assertEqual(1, l2.editorWidgetSetup(l2.fields().indexFromName('signature_temoin')).config()['RelativeStorage'])

    def test_custom_field_configuration_persists_in_project(self):
        layer = QgsVectorLayer('Point?field=visa:string', 'Test', 'memory')
        project = QgsProject.instance()
        project.addMapLayer(layer)
        configure_signatures(layer, ['visa'])
        self.assertIn('visa', json.loads(layer.customProperty('Merifield/signature_fields')))
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(project.write(str(Path(tmp) / 'test.qgs')))
            again = QgsProject()
            self.assertTrue(again.read(str(Path(tmp) / 'test.qgs')))
            other = next(iter(again.mapLayers().values()))
            self.assertIn('visa', signature_names(other))
            self.assertEqual('ExternalResource', other.editorWidgetSetup(0).type())


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.old = plugins.get('qfieldsync')
        self.manager = SimpleNamespace(url='https://old.example/', preferences=SimpleNamespace(value=lambda key: 'stored-auth'),
            is_authenticated=lambda: True, set_url=Mock(), is_login_active=False)
        self.plugin = SimpleNamespace(network_manager=self.manager, show_cloud_overview_dialog=Mock())
        plugins['qfieldsync'] = self.plugin

    def tearDown(self):
        if self.old is None:
            plugins.pop('qfieldsync', None)
        else:
            plugins['qfieldsync'] = self.old

    def test_does_not_send_credentials_to_another_host(self):
        with self.assertRaisesRegex(ValueError, 'autre serveur'):
            SyncBridge().cloud('https://new.example/')
        self.manager.set_url.assert_not_called()

    def test_changes_server_only_without_account(self):
        self.manager.is_authenticated = lambda: False
        self.manager.preferences.value = lambda key: ''
        SyncBridge().cloud('https://new.example/')
        self.manager.set_url.assert_called_once_with('https://new.example/')
        self.plugin.show_cloud_overview_dialog.assert_called_once()

    def test_https_and_host_required(self):
        for value in ['http://server/', 'https://user:password@host/', 'https://', 'https://host/?token=123']:
            with self.assertRaises(ValueError):
                normalize_server(value)
        self.assertEqual('https://host/', normalize_server('https://HOST/api/v1/'))


class GuiTests(unittest.TestCase):
    def test_load_show_refresh_and_unload(self):
        window = QMainWindow()
        iface = SimpleNamespace(mainWindow=lambda: window, activeLayer=lambda: None,
            addPluginToMenu=Mock(), addToolBarIcon=Mock(), removePluginMenu=Mock(), removeToolBarIcon=Mock())
        plugin = MerifieldSync(iface)
        plugin.initGui()
        plugin.run()
        app.processEvents()
        self.assertEqual(4, plugin.dialog.tabs.count())
        self.assertFalse(plugin.action.icon().isNull())
        if '--screenshot' in sys.argv:
            plugin.dialog.grab().save('/tmp/merifield-sync-ui.png')
        plugin.unload()
        iface.removePluginMenu.assert_called_once()
        window.close()


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
