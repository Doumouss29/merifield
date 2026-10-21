# Mérifield

Application de collecte SIG terrain de **Méridien**, dérivée de [QField](https://github.com/opengisch/QField).

![Logo Mérifield](branding/merifield/merifield_logo.svg)

## Première version : 0.1.0 preview

- Nom, logo sans texte et thème orange / bleu marine Mérifield.
- Identifiant Android distinct : `ch.opengis.merifield`, pour cohabiter avec QField.
- Moteur QGIS, formats de projet, formulaires, GPS et synchronisation QFieldCloud conservés.
- Adresse du serveur accessible sur l'écran de connexion ; laisser vide pour QFieldCloud.
- Compilation Android ARM64 via GitHub Actions, sans publication automatique sur les stores.

**État : sources personnalisées ; application à compiler et à valider sur appareil.**
La compatibilité est un objectif reposant sur le moteur amont conservé, pas une certification.

## Installer la préversion Android

Après l’import automatique initial, dans l'onglet **Actions**, ouvrir **Mérifield Android preview**, puis l'exécution terminée avec succès.
Télécharger l'artefact `merifield-android-arm64-preview`, extraire le ZIP et installer l'APK sur un appareil Android ARM64.
La première compilation reconstruit les dépendances QGIS/Qt et peut prendre plusieurs heures ou nécessiter un runner plus puissant.
Aucun APK n'est disponible tant que la compilation n'a pas abouti.

Cette préversion utilise une signature de développement. La clé créée sur un runner temporaire n'est pas conservée : une nouvelle compilation peut nécessiter une désinstallation préalable. **Exporter toutes les données et synchroniser avant toute désinstallation.** Une signature durable sera mise en place avant distribution aux équipes.

## QGIS et QFieldCloud

Préparer les projets dans QGIS avec QFieldSync comme habituellement, puis se connecter au compte QFieldCloud depuis Mérifield. Pour les premiers essais, utiliser un projet de test et une copie des données.

Le futur serveur sera une instance auto-hébergée de QFieldCloud. Le changement d'adresse ne migre pas les comptes ni les projets automatiquement.
Voir [cloud et migration](docs/merifield/CLOUD.md) et [validation terrain](docs/merifield/VALIDATION.md).

## Développement et suivi amont

Base importée : `opengisch/QField`, commit `f597347f84e4d5549bd4b33629d2888bf631a8b3` (21 octobre 2026).
Les sources amont sont importées comme un instantané identifié par ce commit ; le dépôt amont conserve l'historique complet.

Les options CMake `APP_NAME`, `APP_ICON`, `APP_ICON_PATH`, `APP_THEME_PATH` et `APP_PACKAGE_NAME` portent la personnalisation.
Les modules, identifiants de classes internes et protocoles QField sont volontairement conservés.

```bash
python3 scripts/merifield/verify.py
bash test/test_version_number.sh
```

Voir le [README amont](docs/merifield/UPSTREAM_README.md) pour les dépendances et les procédures de développement natives.
Les workflows de publication et de services propres à OPENGIS.ch ont été retirés de cette version dérivée.

## Licence et attribution

Mérifield est un projet dérivé indépendant, non présenté comme une application officielle OPENGIS.ch.
Les licences, mentions et crédits QField/QGIS et de leurs dépendances sont conservés. Voir [LICENSE](LICENSE), [LICENSE.txt](LICENSE.txt) et les en-têtes des fichiers. La distribution de versions modifiées doit respecter ces licences, notamment la mise à disposition du code source correspondant.
