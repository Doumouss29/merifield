"""Project and signature operations; no credentials or network requests here."""
# SPDX-License-Identifier: GPL-3.0-or-later
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from qgis.core import (QgsEditorWidgetSetup, QgsField, QgsMapLayerType,
                       QgsProject, QgsProviderRegistry, QgsVectorDataProvider)
from qgis.PyQt.QtCore import QVariant

SIGNATURE_PROPERTY = 'Merifield/signature_fields'


def normalize_server(url):
    parts = urlsplit(url.strip())
    if (parts.scheme != 'https' or not parts.hostname or parts.username
            or parts.password or parts.query or parts.fragment):
        raise ValueError('Saisir une adresse HTTPS sans identifiants, paramètres ni fragment.')
    path = parts.path.rstrip('/')
    if path.endswith('/api/v1'):
        path = path[:-7]
    return urlunsplit(('https', parts.netloc.lower(), path + '/', '', ''))


def signature_names(layer):
    try:
        stored = json.loads(layer.customProperty(SIGNATURE_PROPERTY, '[]'))
    except (ValueError, TypeError):
        stored = []
    if not isinstance(stored, list):
        stored = []
    return list(dict.fromkeys([f.name() for f in layer.fields()
                              if f.name().lower().startswith('signature_')]
                             + [n for n in stored if isinstance(n, str)]))


def configure_signatures(layer, names):
    """Add missing text columns in a new edit session, then configure attachments.

    Never commit an edit session opened by the user. Configuration is stored in
    the QGIS project; no default value overwrites an existing image path.
    """
    names = list(dict.fromkeys(n.strip() for n in names if n.strip()))
    if not names:
        raise ValueError('Choisir au moins un champ de signature.')
    if not layer or layer.type() != QgsMapLayerType.VectorLayer or not layer.isValid():
        raise ValueError('Sélectionner une couche vectorielle valide.')
    for name in names:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,62}', name):
            raise ValueError('Nom de champ invalide : ' + name)
        i = layer.fields().indexFromName(name)
        if i >= 0 and layer.fields()[i].type() != QVariant.String:
            raise ValueError('Le champ doit être de type texte : ' + name)
    if len({n.lower() for n in names}) != len(names):
        raise ValueError('Les noms de champs doivent être distincts, même sans tenir compte des majuscules.')
    missing = [n for n in names if layer.fields().indexFromName(n) < 0]
    if missing and 'shapefile' in layer.storageType().lower() and any(len(n) > 10 for n in missing):
        raise ValueError('Le Shapefile limite les noms à 10 caractères. Utiliser des noms courts ou convertir la couche en GeoPackage.')
    if missing:
        if layer.isEditable():
            raise ValueError('Enregistrer ou annuler les modifications de la couche avant de créer des champs.')
        if not layer.dataProvider().capabilities() & QgsVectorDataProvider.AddAttributes:
            raise ValueError('Cette source ne permet pas l’ajout de champs. Utiliser un GeoPackage ou créer les colonnes en base.')
        if not layer.startEditing():
            raise ValueError('Impossible de modifier la structure de la couche.')
        try:
            for name in missing:
                if not layer.addAttribute(QgsField(name, QVariant.String, len=512)):
                    raise ValueError('Impossible de créer ' + name)
            if not layer.commitChanges():
                raise ValueError('Échec de création : ' + '; '.join(layer.commitErrors()))
        except Exception:
            layer.rollBack()
            raise
    for name in names:
        idx = layer.fields().indexFromName(name)
        if idx < 0:
            raise ValueError('Le fournisseur a modifié le nom de champ : ' + name + '. Actualiser la couche puis choisir le nom réel.')
        layer.setEditorWidgetSetup(idx, QgsEditorWidgetSetup('ExternalResource', {
            'DocumentViewer': 1, 'RelativeStorage': 1, 'StorageMode': 0,
            'FileWidget': True, 'UseLink': False, 'DocumentViewerHeight': 180,
        }))
        if not layer.attributeAlias(idx):
            layer.setFieldAlias(idx, name.replace('_', ' ').capitalize())
    layer.setCustomProperty(SIGNATURE_PROPERTY,
                           json.dumps(list(dict.fromkeys(signature_names(layer) + names))))
    QgsProject.instance().setDirty(True)
    return missing


def local_source(layer):
    """Return the local file path known to the QGIS provider, if any."""
    if layer.providerType() in ('postgres', 'wms', 'wfs', 'xyz', 'arcgisfeatureserver', 'arcgismapserver', 'memory'):
        return None
    try:
        decoded = QgsProviderRegistry.instance().decodeUri(layer.providerType(), layer.source())
        path = decoded.get('path') or decoded.get('databaseName') or ''
        if path and not str(path).startswith(('/vsi', 'http:', 'https:')):
            return Path(path)
    except Exception:
        pass
    return None


def diagnose(project):
    findings = []
    if not project.fileName():
        findings.append(('Erreur', 'Enregistrer le projet QGIS avant le paquetage.'))
    if project.isDirty():
        findings.append(('Attention', 'Le projet comporte des changements non enregistrés.'))
    for layer in project.mapLayers().values():
        name = layer.name()
        if not layer.isValid():
            findings.append(('Erreur', name + ' : source inaccessible.'))
            continue
        if layer.type() == QgsMapLayerType.VectorLayer:
            if layer.isEditable():
                findings.append(('Erreur', name + ' : terminer la session de modification avant le paquetage.'))
            if layer.providerType() == 'memory':
                findings.append(('Erreur', name + ' : enregistrer la couche temporaire sur disque.'))
            if layer.providerType() == 'postgres':
                findings.append(('Attention', name + ' : définir le mode hors connexion et une clé stable dans QFieldSync ; vérifier les accès du cloud à PostGIS.'))
            for field in signature_names(layer):
                idx = layer.fields().indexFromName(field)
                if idx < 0:
                    findings.append(('Erreur', name + ' : champ de signature manquant ' + field))
                    continue
                setup = layer.editorWidgetSetup(idx)
                if setup.type() != 'ExternalResource' or setup.config().get('RelativeStorage') != 1:
                    findings.append(('Attention', name + ' / ' + field + ' : configurer une pièce jointe avec chemin relatif au projet.'))
        if layer.providerType().lower() in ('wms', 'wfs', 'xyz', 'arcgisfeatureserver', 'arcgismapserver'):
            findings.append(('Attention', name + ' : service réseau, disponibilité hors connexion à vérifier.'))
        path = local_source(layer)
        if path and not path.is_file():
            findings.append(('Erreur', name + ' : fichier local introuvable.'))
    return findings or [('OK', 'Aucun problème détecté par les contrôles de base. Vérifier le paquet sur téléphone.')]
