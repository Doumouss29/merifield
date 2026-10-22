# Test des signatures Mérifield

Nécessite le nouvel APK incluant la fonction de signature ; l’ancien APK ne propose pas ce bouton.

1. Extraire tout le ZIP dans un dossier accessible à Mérifield, sans séparer les fichiers.
2. Dans Mérifield, ouvrir le projet local `Test_signatures.qgs`.
3. Toucher le point orange situé à Abidjan, ouvrir sa fiche et passer en modification (crayon).
4. Renseigner les noms, puis toucher l’icône de dessin du champ « Signature du demandeur ».
5. Signer au doigt, essayer « Effacer », signer à nouveau et valider avec la coche en haut à droite.
6. Faire une seconde signature différente dans « Signature du témoin ».
7. Enregistrer le formulaire, fermer et rouvrir le projet : les deux images doivent être conservées.
8. Vérifier les fichiers PNG créés dans `DCIM` et les chemins dans les deux champs.

Tests complémentaires : Annuler/Retour doit conserver l’ancienne signature ; après Effacer, la coche reste désactivée tant qu’aucun tracé n’est présent. Vérifier le mode avion et la rotation du téléphone. Les données sont fictives et le projet ne nécessite aucun fond de carte ni cloud.

Dans QGIS : les champs sont de type texte avec widget « Pièce jointe », aperçu image et chemin relatif au projet. Dans Mérifield, le préfixe `signature_` active la saisie. Plusieurs champs peuvent être configurés ainsi. Pour un autre nom, définir la propriété personnalisée de couche `Merifield/signature_fields` comme tableau JSON de noms de champs.

Pour un projet de production : privilégier GeoPackage ou PostGIS. Ce petit GeoJSON sert uniquement de démonstration. La synchronisation des PNG via le cloud reste à tester ; le ZIP local permet de tester d’abord la saisie et la persistance sans cloud. Une image manuscrite n’est pas une signature électronique certifiée.
