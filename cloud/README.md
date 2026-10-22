# Mérifield Cloud — première version du portail et kit de déploiement

Cette version ajoute un portail français au moteur QFieldCloud auto-hébergé. Elle est préparée pour un pilote sur VPS ; elle n’est pas mise en ligne par la simple création de ces sources.

## Fonctionnalités livrées

- Connexion et création de compte via l’authentification native du moteur ; vérification d’e-mail obligatoire dans la configuration de production.
- Espaces personnels et entreprises, sélection de l’espace et projets privés.
- Création d’un espace entreprise, création de projets, publication de leurs données depuis QGIS/Mérifield Sync.
- Consommation et limite de stockage issues du moteur, pas d’un compteur parallèle.
- Consultation des derniers traitements ; liste des fichiers et téléchargement avec les permissions natives.
- Invitations par e-mail, acceptation sous 7 jours par le compte correspondant à l’adresse invitée, contrôle des droits actuels de l’invitant et du nombre de membres.
- Catalogue d’offres modifiable, demande mensuelle/annuelle, validation ou refus par le superadministrateur, historique de traitement.
- Activation manuelle qui remplace l’abonnement dans le moteur et applique son quota effectif.
- Identité Mérifield dans le portail, la connexion, le thème d’administration et les notifications adaptées. Noms techniques et mentions légales des composants conservés.

## Abonnements : fonctionnement du pilote

Les offres et limites initiales sont provisoires et modifiables. Aucun prix n’est fixé. Les offres publiées sont Découverte, Professionnel, Équipe et Entreprise pour les organisations, ainsi qu’une offre Professionnel individuel pour les comptes personnels.

Les valeurs de départ sont respectivement 1 000, 10 000, 50 000 et 100 000 Mo par organisation, avec 2, 5, 20 et 100 personnes au total (propriétaire compris). L’offre individuelle prévoit 10 000 Mo. Ce sont des forfaits globaux, pas un calcul par siège. Le compte personnel de départ reçoit 1 000 Mo. PostGIS est activé dans ces plans pilotes pour permettre les essais.

- **Quota et fonctionnalités techniques** : administration → Plans du moteur.
- **Nom, description et tarifs affichés** : administration → Offres Mérifield.
- Une offre référence le code d’un plan technique. Modifier le quota de ce plan affecte les comptes qui l’utilisent ; créer une nouvelle offre/plan si des clients doivent conserver leurs anciennes conditions.
- `merifield_seed` crée les valeurs initiales et n’écrase pas les modifications ultérieures.
- Les versions de fichiers conservées participent à la consommation telle que calculée par le moteur. Le coût physique des sauvegardes et les éventuelles anciennes versions côté stockage S3 doivent être dimensionnés séparément.

**La périodicité est une préférence enregistrée, pas un mécanisme de renouvellement.** Cette version ne prélève pas de paiement, ne génère pas de facture fiscale, ne synchronise pas de prestataire de paiement et ne suspend pas automatiquement pour impayé. L’administrateur accorde manuellement l’accès au pilote ; les conditions d’expiration et le paiement seront ajoutés après définition des offres. Le statut interne du moteur `active_paid` signifie ici accès accordé ; il ne prouve aucun paiement et ne doit pas être exporté comme une recette.

## Infrastructure à fournir

Pour un pilote : VPS Ubuntu 24.04 x86_64, 4 vCPU/16 Go RAM/200 Go SSD comme hypothèse de départ ; adapter après mesure des traitements et des projets.

- Docker Engine et plugin Docker Compose v2.
- Domaine public pointant vers le VPS, ports TCP 80 et 443 accessibles.
- Bucket S3 compatible existant et accès au bucket ; endpoint HTTPS accessible aux clients et aux workers. Configurer la rétention/versioning selon le fournisseur et tester un upload/download réel.
- SMTP authentifié sur le port 587 avec STARTTLS et expéditeur validé. La configuration initiale peut être adaptée à un autre port dans `.env`.
- Sauvegarde hors du VPS pour PostgreSQL, les médias et les fichiers S3 ; copie protégée de `.env` et des clés de chiffrement.

PostGIS et le cache sont privés au réseau Docker. Caddy termine le HTTPS et obtient le certificat. Le worker du moteur utilise le socket Docker de l’hôte pour démarrer les traitements QGIS : conserver ce VPS dédié et ne pas ouvrir cet accès aux clients. Le moteur QGIS est construit séparément, une première fois ; les couches Docker persistent pour les builds suivants.

## Préparation sur le VPS

Les sources du moteur sont verrouillées au commit `46f0292db3c7786cbd291f19d2a7ced87db05517`. Le script télécharge ce commit et ses sous-modules, puis applique l’extension sans remplacer les routes API `/api/v1/`.

Depuis les sources Mérifield :

```bash
python3 cloud/deploy/bootstrap.py /opt/merifield-engine
cd /opt/merifield-engine
python3 merifield-deploy/configure.py
```

Le dossier destination ne doit pas exister. La configuration pose les questions nécessaires et génère des secrets aléatoires dans un `.env` de mode 0600. Elle refuse d’écraser un `.env` existant. Les paramètres secrets ne doivent pas être envoyés dans la conversation ou ajoutés à Git.

Vérifier la configuration sans afficher les secrets, puis construire et initialiser :

```bash
docker compose config --quiet
docker compose up -d db memcached
docker compose build app worker_wrapper qgis3
docker compose run --rm app python manage.py migrate
docker compose run --rm app python manage.py merifield_seed
docker compose run --rm app python manage.py createsuperuser
docker compose run --rm app python manage.py collectstatic --noinput
docker compose up -d app worker_wrapper ofelia caddy
```

Le pilote utilise le worker QGIS 3. Si des projets QGIS 4 sont publiés, construire aussi le service `qgis4` après vérification de la compatibilité mobile.

Le worker peut avoir besoin des grilles PROJ pour certains systèmes de coordonnées : les installer dans le volume `transformation_grids` selon les projets, ou exécuter le service de maintenance `mirror_transformation_grids` après évaluation du volume et de la connexion.

Après la mise en route :

```bash
curl --fail https://votre-domaine/api/v1/status/
docker compose logs --tail=100 app worker_wrapper caddy
```

L’endpoint `/healthz/` indique uniquement que le portail répond. `/api/v1/status/` vérifie les services du moteur, notamment la base et le stockage. Ajouter la surveillance de ces endpoints et des échecs de traitements.

Configurer la même URL racine HTTPS dans Mérifield Android et dans Mérifield Sync/QFieldSync, puis valider sur une copie de projet.

## Recette avant ouverture

1. Créer deux comptes et deux entreprises ; vérifier qu’un compte ne voit ni ne télécharge les données de l’autre.
2. Envoyer une invitation, vérifier le mail et l’acceptation avec le bon compte.
3. Publier un projet GeoPackage depuis QGIS, le télécharger sur deux téléphones, collecter hors connexion et synchroniser.
4. Vérifier les photos et les deux signatures PNG dans les deux sens.
5. Tester un dépassement de stockage via l’API/plugin, puis une activation d’offre ; contrôler le quota côté serveur.
6. Tester un projet PostGIS avec UUID et droits limités, puis les conflits et les triggers au retour.
7. Tester une restauration de sauvegarde avant de confier des données uniques au service.

## Sauvegarde et restauration

`bash merifield-deploy/backup.sh /chemin/sauvegardes` produit un dump PostgreSQL au format personnalisé. Il ne sauvegarde pas à lui seul les objets S3, les médias, les volumes Caddy ni les secrets ; prévoir leur sauvegarde et rétention externe. Planifier ce script sur le VPS après installation et vérifier régulièrement une restauration.

Pour restaurer dans une **nouvelle** instance de recette : arrêter les traitements, recréer une base vide, restaurer avec `pg_restore` sur cette nouvelle base, remettre les fichiers/médias correspondants et les mêmes clés de chiffrement, puis effectuer la recette de synchronisation. Ne pas restaurer directement par-dessus une base de production active.

## Vérification des sources

```bash
python -m pip install 'Django>=5.2,<5.3' 'PyYAML>=6,<7'
python cloud/manage_local_tests.py test tests --verbosity 2
python cloud/manage_local_tests.py makemigrations --check --dry-run
python cloud/package.py
```

Les tests locaux utilisent un adaptateur de test en mémoire pour vérifier le portail, les frontières d’accès, les invitations et la validation des demandes. Ils ne constituent pas une recette réelle de la synchronisation.

La CI `Mérifield Cloud platform` ajoute une intégration dans le véritable moteur avec PostgreSQL/PostGIS : espaces, projet privé, activation réelle du quota et absence d’écrasement des offres éditées. La compilation Docker et l’exécution des workers QGIS, le fournisseur S3, l’e-mail réel et la collecte mobile restent à vérifier dans l’environnement de déploiement.

## Licences

Le moteur QFieldCloud est sous licence MIT, copyright OPENGIS.ch. Son texte est conservé dans `UPSTREAM_LICENSE` et dans le checkout préparé. Les crédits sont accessibles dans le portail. Ce portail constitue une adaptation indépendante ; il n’est pas un service officiel d’OPENGIS.ch. Les composants tiers conservent leurs licences. Les conditions commerciales, l’identité de l’exploitant et les mentions de confidentialité doivent être finalisées avant l’ouverture publique.
