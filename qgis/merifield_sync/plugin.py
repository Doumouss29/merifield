"""Mérifield Sync QGIS user interface."""
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import shutil
from pathlib import Path

from qgis.core import QgsMapLayerType, QgsProject, QgsSettings
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (QAction, QComboBox, QDialog, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from .archive import create_zip, folder_files
from .bridge import SyncBridge
from .core import configure_signatures, diagnose, local_source, normalize_server, signature_names

ROOT = Path(__file__).parent


class MerifieldSync:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        self.action = QAction(QIcon(str(ROOT / 'icon.svg')), 'Mérifield Sync', self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu('Mérifield', self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.action:
            self.iface.removePluginMenu('Mérifield', self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def run(self):
        if self.dialog is None:
            self.dialog = SyncDialog(self.iface)
        self.dialog.refresh_layers()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()


class SyncDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.bridge = SyncBridge()
        self.settings = QgsSettings()
        self.setWindowTitle('Mérifield Sync · 0.1.0')
        self.resize(800, 620)
        layout = QVBoxLayout(self)
        header = QLabel('MÉRIFIELD SYNC\nPréparez votre projet. Collectez sur le terrain.')
        header.setStyleSheet('background:#14213d;color:white;padding:20px;font-size:19px;border-radius:8px;')
        layout.addWidget(header)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.build_project_tab()
        self.build_signature_tab()
        self.build_local_tab()
        self.build_cloud_tab()
        footer = QLabel('Mérifield utilise QFieldSync pour le paquetage et la synchronisation. Version de test.')
        footer.setWordWrap(True)
        layout.addWidget(footer)
        close = QPushButton('Fermer')
        close.clicked.connect(self.close)
        layout.addWidget(close, alignment=Qt.AlignRight)

    def tab(self, name, text):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label)
        self.tabs.addTab(widget, name)
        return layout

    def button(self, layout, title, callback):
        button = QPushButton(title)
        button.setMinimumHeight(34)
        button.clicked.connect(lambda _checked=False: self.guarded(callback))
        layout.addWidget(button)
        return button

    def guarded(self, callback):
        try:
            callback()
        except Exception as error:
            QMessageBox.warning(self, 'Mérifield Sync', str(error))

    def build_project_tab(self):
        layout = self.tab('1 · Projet', 'Vérifiez les sources, les sessions de modification et les champs de signature avant le transfert.')
        self.project_label = QLabel()
        self.project_label.setWordWrap(True)
        layout.addWidget(self.project_label)
        self.report = QTextBrowser()
        layout.addWidget(self.report)
        self.button(layout, 'Vérifier le projet', self.check_project)
        self.button(layout, 'Enregistrer le projet QGIS', self.save_project)
        self.button(layout, 'Configurer les couches hors connexion…', lambda: self.sync_action('show_project_configuration_dialog'))
        self.button(layout, 'Copier le projet d’exemple à deux signatures…', self.copy_example)

    def build_signature_tab(self):
        layout = self.tab('2 · Signatures', 'Chaque signature utilise un champ texte avec le widget Pièce jointe. La saisie au doigt nécessite le nouvel APK Mérifield. QGIS affiche ensuite les images enregistrées.')
        form = QFormLayout()
        self.layers = QComboBox()
        self.layers.currentIndexChanged.connect(self.show_layer_fields)
        self.fields = QLineEdit('signature_demandeur, signature_temoin')
        self.fields.setPlaceholderText('Noms séparés par des virgules')
        self.layer_info = QLabel()
        self.layer_info.setWordWrap(True)
        form.addRow('Couche', self.layers)
        form.addRow('Champs de signature', self.fields)
        form.addRow(self.layer_info)
        layout.addLayout(form)
        label = QLabel('Les champs manquants seront créés. Les données existantes sont conservées. Enregistrez ensuite le projet pour conserver le formulaire.')
        label.setWordWrap(True)
        layout.addWidget(label)
        self.button(layout, 'Créer / configurer les champs de signature', self.apply_signatures)
        self.button(layout, 'Actualiser les couches', self.refresh_layers)
        layout.addStretch()

    def build_local_tab(self):
        layout = self.tab('3 · ZIP terrain', 'Préparez d’abord un dossier autonome avec QFieldSync, puis archivez ce dossier. Pour PostGIS, choisissez le mode hors connexion dans la configuration QFieldSync.')
        self.button(layout, 'A · Préparer le dossier terrain avec QFieldSync…', lambda: self.sync_action('show_package_dialog'))
        row = QHBoxLayout()
        self.folder = QLineEdit()
        self.folder.setPlaceholderText('Dossier préparé par QFieldSync')
        row.addWidget(self.folder)
        choose = QPushButton('Parcourir…')
        choose.clicked.connect(self.choose_folder)
        row.addWidget(choose)
        layout.addLayout(row)
        self.button(layout, 'B · Créer le ZIP du dossier préparé…', self.export_zip)
        self.button(layout, 'Récupérer les modifications terrain avec QFieldSync…', lambda: self.sync_action('show_synchronize_dialog', require_ready=False))
        help_label = QLabel('Extraire le ZIP complet sur le téléphone, puis ouvrir le projet dans Mérifield. Pour le retour terrain, récupérer tout le dossier modifié (base et DCIM) et utiliser la synchronisation QFieldSync ; ne pas écraser la base source avec la copie terrain.')
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        layout.addStretch()

    def build_cloud_tab(self):
        layout = self.tab('4 · Cloud', 'Publiez et récupérez vos projets dans la fenêtre QFieldSync. Le serveur personnalisé doit être compatible avec l’API QFieldCloud ; cette extension ne déploie pas de serveur.')
        self.destinations = QComboBox()
        self.destinations.addItem('QFieldCloud', 'https://app.qfield.cloud/')
        try:
            urls = json.loads(self.settings.value('MerifieldSync/servers', '[]'))
        except (TypeError, ValueError):
            urls = []
        for url in urls if isinstance(urls, list) else []:
            try:
                normal = normalize_server(url)
                if self.destinations.findData(normal) < 0:
                    self.destinations.addItem(normal, normal)
            except (TypeError, ValueError):
                continue
        layout.addWidget(self.destinations)
        self.server = QLineEdit()
        self.server.setPlaceholderText('https://cloud.votre-domaine.ci/')
        layout.addWidget(self.server)
        self.button(layout, 'Mémoriser ce serveur', self.add_server)
        self.button(layout, 'Ouvrir les projets / publier sur le serveur choisi…', self.open_cloud)
        self.button(layout, 'Synchroniser le projet cloud courant…', lambda: self.sync_action('open_cloud_synchronize_dialog'))
        self.button(layout, 'Préférences et comptes QFieldSync…', lambda: self.sync_action('show_preferences_dialog', require_ready=False))
        info = QLabel('Les mots de passe restent gérés par QFieldSync et le gestionnaire d’authentification QGIS. Le changement de serveur exige de déconnecter l’ancien compte. La synchronisation du projet courant utilise le serveur déjà configuré dans QFieldSync.')
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()

    def refresh_layers(self):
        project = QgsProject.instance()
        self.project_label.setText('Projet : ' + (project.fileName() or 'non enregistré'))
        active = self.iface.activeLayer()
        previous = self.layers.currentData()
        self.layers.blockSignals(True)
        self.layers.clear()
        for layer in sorted(project.mapLayers().values(), key=lambda x: x.name()):
            if layer.type() == QgsMapLayerType.VectorLayer:
                self.layers.addItem(layer.name(), layer.id())
        wanted = active.id() if active else previous
        idx = self.layers.findData(wanted)
        if idx >= 0:
            self.layers.setCurrentIndex(idx)
        self.layers.blockSignals(False)
        self.show_layer_fields()
        self.check_project()

    def selected_layer(self):
        return QgsProject.instance().mapLayer(self.layers.currentData())

    def show_layer_fields(self, *_args):
        layer = self.selected_layer()
        if layer:
            self.layer_info.setText('Champs texte existants : ' + ', '.join(f.name() for f in layer.fields() if f.typeName().lower() in ('text', 'string', 'varchar')))
            names = signature_names(layer)
            self.fields.setText(', '.join(names) if names else 'signature_demandeur, signature_temoin')
        else:
            self.layer_info.setText('Ajouter une couche vectorielle au projet.')

    def check_project(self):
        self.report.clear()
        for level, text in diagnose(QgsProject.instance()):
            self.report.append('[' + level + '] ' + text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

    def save_project(self):
        # QGIS owns Save As and the existing project identity.
        self.iface.actionSaveProject().trigger()
        self.refresh_layers()

    def require_ready(self):
        errors = [text for level, text in diagnose(QgsProject.instance()) if level == 'Erreur']
        if errors:
            raise ValueError('\n'.join(errors))
        if QgsProject.instance().isDirty():
            raise ValueError('Enregistrer le projet avant le paquetage ou la synchronisation.')

    def sync_action(self, method, require_ready=True):
        if require_ready:
            self.require_ready()
        self.bridge.call(method)

    def apply_signatures(self):
        names = [name.strip() for name in self.fields.text().split(',')]
        added = configure_signatures(self.selected_layer(), names)
        self.check_project()
        QMessageBox.information(self, 'Signatures configurées', 'Configuration appliquée.' + (' Champs créés : ' + ', '.join(added) if added else '') + '\nEnregistrer le projet QGIS pour conserver cette configuration.')

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, 'Choisir uniquement le dossier terrain préparé', self.folder.text())
        if folder:
            self.folder.setText(folder)

    def export_zip(self):
        root = Path(self.folder.text()).resolve() if self.folder.text().strip() else None
        if root is None:
            raise ValueError('Choisir le dossier préparé par QFieldSync.')
        files = folder_files(root)
        for layer in QgsProject.instance().mapLayers().values():
            path = local_source(layer)
            if path and (root == path.resolve().parent or root in path.resolve().parents) and layer.type() == QgsMapLayerType.VectorLayer and layer.isEditable():
                raise ValueError('Terminer les modifications des couches du dossier avant de créer le ZIP.')
        # Verify project data sources, without replacing the user's open project.
        warnings = []
        for file in files:
            if file.suffix.lower() not in ('.qgs', '.qgz'):
                continue
            project = QgsProject()
            if not project.read(str(file)):
                raise ValueError('Projet illisible : ' + file.name)
            for layer in project.mapLayers().values():
                if not layer.isValid():
                    raise ValueError('Source inaccessible dans le paquet : ' + layer.name())
                path = local_source(layer)
                if path and root not in path.resolve().parents:
                    raise ValueError('Source en dehors du dossier terrain : ' + layer.name() + '. Refaire le paquetage avec QFieldSync.')
                if layer.providerType() in ('postgres', 'memory'):
                    raise ValueError('La couche ' + layer.name() + ' n’est pas une copie locale autonome. Refaire le paquetage en mode hors connexion.')
                if layer.providerType() in ('wms', 'wfs', 'xyz', 'arcgisfeatureserver', 'arcgismapserver'):
                    warnings.append(layer.name())
        if warnings:
            answer = QMessageBox.question(self, 'Couches réseau', 'Ces couches nécessitent du réseau : ' + ', '.join(warnings) + '\nCréer le ZIP quand même ?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if answer != QMessageBox.Yes:
                return
        destination, _ = QFileDialog.getSaveFileName(self, 'Créer le ZIP terrain (hors du dossier préparé)', str(root.parent / (root.name + '.zip')), 'Archive ZIP (*.zip)')
        if not destination:
            return
        if not destination.lower().endswith('.zip'):
            destination += '.zip'
        count = create_zip(root, destination)
        QMessageBox.information(self, 'ZIP créé', str(count) + ' fichiers archivés.\n' + destination)

    def add_server(self):
        url = normalize_server(self.server.text())
        index = self.destinations.findData(url)
        if index < 0:
            self.destinations.addItem(url, url)
            index = self.destinations.count() - 1
        self.destinations.setCurrentIndex(index)
        urls = [self.destinations.itemData(i) for i in range(1, self.destinations.count())]
        self.settings.setValue('MerifieldSync/servers', json.dumps(urls))

    def open_cloud(self):
        self.bridge.cloud(self.destinations.currentData())

    def copy_example(self):
        parent = QFileDialog.getExistingDirectory(self, 'Choisir le dossier parent du projet exemple')
        if not parent:
            return
        destination = Path(parent) / 'Merifield_Test_Signatures'
        if destination.exists():
            raise ValueError('Le dossier Merifield_Test_Signatures existe déjà. Choisir un autre emplacement pour conserver ses données.')
        shutil.copytree(ROOT / 'example', destination)
        QMessageBox.information(self, 'Exemple copié', 'Ouvrir Test_signatures.qgs dans ce dossier :\n' + str(destination) + '\nLe même dossier peut être transféré sur le téléphone avec le nouvel APK Mérifield.')
