# Mérifield Sync — extension QGIS 0.1.0

Extension expérimentale pour QGIS 3.34–3.99. Le code Mérifield est sous GPL-3.0-or-later. QFieldSync est une dépendance externe, développée par OPENGIS.ch et ses contributeurs ; ses noms et ses mentions légales sont conservés. Mérifield n’est pas une application officielle d’OPENGIS.ch.

## Installation

1. QGIS → **Extensions → Installer/Gérer les extensions → Installer depuis un ZIP**.
2. Choisir `Merifield_Sync_QGIS_0.1.0.zip`, puis activer **Mérifield Sync**.
3. Installer et activer **QFieldSync** dans le gestionnaire d’extensions. Utiliser une version compatible avec votre version de QGIS.
4. Cliquer sur l’icône Mérifield ou sur **Extensions → Mérifield → Mérifield Sync**.

Les onglets Projet et Signatures fonctionnent sans QFieldSync. Le paquetage, les échanges cloud et le retour terrain utilisent les fenêtres de QFieldSync installé ; ce plugin ne contient pas un second moteur de synchronisation.

## Projet et signatures

Ouvrir un projet puis choisir sa couche dans **Signatures**. Saisir les noms de champs séparés par des virgules, par exemple `signature_demandeur, signature_temoin, signature_geometre`. Cliquer sur **Créer / configurer**. Les champs manquants sont créés comme texte, les champs existants conservent leurs valeurs. Si des modifications sont en cours, les enregistrer ou les annuler avant d’ajouter des colonnes. Pour PostGIS, l’utilisateur doit avoir le droit de modifier la structure, sinon créer les colonnes en base au préalable.

Les champs utilisent le widget natif **Pièce jointe**, aperçu image et stockage relatif au projet. La propriété de couche `Merifield/signature_fields` indique les champs au mobile. Enregistrer le projet après configuration. Un formulaire QGIS personnalisé doit également afficher ces champs : ajouter les widgets dans le concepteur de formulaire si nécessaire.

La saisie au doigt nécessite l’APK Mérifield incluant la mise à jour signature. QGIS affiche la pièce jointe ; cette extension n’ajoute pas une zone de signature dessinée dans QGIS lui-même. Les images sont conservées dans `DCIM`. Le projet exemple peut être copié depuis l’onglet Projet sans remplacer un projet existant.

## ZIP local et retour terrain

1. Enregistrer les couches et le projet.
2. Utiliser **Configurer les couches hors connexion** (QFieldSync), définir les actions des couches et inclure `DCIM` parmi les dossiers de pièces jointes.
3. Onglet **ZIP terrain → A**, préparer un nouveau dossier autonome avec QFieldSync. Pour PostGIS, choisir le mode hors connexion adapté ; ne pas faire une simple copie du fichier `.qgs`.
4. Sélectionner ce dossier et utiliser **B** pour créer un ZIP en dehors du dossier terrain. L’archive contient tout le dossier choisi. Ne pas sélectionner un répertoire de travail contenant d’autres documents.
5. Extraire le ZIP complet sur le téléphone et ouvrir le projet dans Mérifield.
6. Au retour, récupérer tout le dossier terrain avec sa base et ses pièces jointes, puis **Récupérer les modifications terrain avec QFieldSync**. Conserver le projet source et son dossier associé. Un ZIP ne fusionne pas automatiquement les changements avec une base.

Le ZIP vérifie les sources accessibles et les références de fichiers extérieures au dossier. Les services réseau peuvent être conservés après confirmation, mais ne deviennent pas disponibles hors connexion. Les liens symboliques sont refusés. La création est atomique : une erreur ne détruit pas une archive précédente.

## QFieldCloud et serveur personnalisé

Choisir QFieldCloud, ou mémoriser une URL HTTPS de serveur compatible QFieldCloud, puis **Ouvrir les projets / publier**. La création, la publication, l’authentification et les transferts se font dans QFieldSync. Les secrets ne sont pas stockés par Mérifield Sync.

Avant de changer de serveur, déconnecter le compte QFieldSync précédent. Le plugin refuse de diriger une session authentifiée vers un autre hôte. **Synchroniser le projet cloud courant** utilise le serveur déjà associé à QFieldSync ; le choix de la liste ne déplace pas un projet existant vers un autre cloud.

Le serveur Mérifield Cloud reste à déployer. La synchronisation réelle PostGIS, les conflits et les pièces jointes doivent être validés sur ce serveur avant production. Les UUID, permissions et triggers restent à configurer selon chaque projet.

## Vérifications développeur

```sh
python3 -m unittest discover -s qgis/tests -p test_archive.py -v
QT_QPA_PLATFORM=offscreen /usr/bin/python3 qgis/tests/test_qgis.py
python3 qgis/package_plugin.py
```

Les tests QGIS nécessitent PyQGIS et Qt. Les appels cloud sont testés avec un adaptateur simulé, sans compte réel. L’interface QFieldSync a été examinée dans le code source officiel au commit `c8abedb9317607f5fd040742ba4071e592dff543` ; le plugin vérifie à l’exécution la présence des méthodes nécessaires et signale les incompatibilités.
