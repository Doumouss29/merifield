# Cloud de Mérifield

## Aujourd'hui

Le serveur par défaut reste `https://app.qfield.cloud`. L'application utilise le client, l'authentification et les échanges de synchronisation amont. Le champ serveur est visible pendant la déconnexion.

## Ensuite : instance propre

Déployer le serveur open source QFieldCloud, en suivant la documentation de la version retenue :
- https://github.com/opengisch/QFieldCloud
- https://docs.qfield.org/reference/qfieldcloud/self_hosted/
- https://docs.qfield.org/get-started/tutorials/advanced-setup-qfc/

Il faudra une infrastructure dimensionnée pour les utilisateurs et les traitements, un nom de domaine avec HTTPS, la base de données, le stockage de fichiers, les workers de traitement, les mails, les sauvegardes et la supervision. Les détails dépendent de la version du serveur retenue. Aucun serveur n'est déployé par ce dépôt et aucune adresse fictive n'est préconfigurée.

## Migration contrôlée

1. Provisionner l'instance et vérifier les sauvegardes/restaurations.
2. Recréer ou migrer comptes, organisations, membres et permissions par les moyens supportés.
3. Synchroniser tous les appareils avec l'ancien service et sauvegarder les projets/données/photos.
4. Publier un projet pilote vers la nouvelle instance avec QFieldSync configuré sur cette adresse.
5. Renseigner la nouvelle URL sur Mérifield ; se connecter avec les identifiants du nouveau serveur.
6. Vérifier téléchargement, collecte hors connexion, envoi des modifications, photos et conflits entre deux appareils.
7. Basculer projet par projet après validation, puis seulement retirer les accès devenus inutiles à l'ancien service.

Le code client n'a pas besoin d'un protocole de synchronisation spécifique Mérifield tant que le serveur conserve les API QFieldCloud compatibles. Une nouvelle interface de gestion cloud pourra être développée dans un dépôt séparé.
