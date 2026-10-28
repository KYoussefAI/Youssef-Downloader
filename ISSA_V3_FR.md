# ISSA Downloader v3 — Français

Version compacte validée : un seul écran, sans navigation superflue.

1. Coller un lien YouTube.
2. Cliquer sur **Analyser** pour consulter le titre et la miniature.
3. Choisir **Vidéo MP4** (qualité au choix) ou **Audio MP3**.
4. Cliquer sur **Télécharger** ; la progression, la vitesse et le temps restant s'affichent.
5. Après téléchargement, cliquer sur **Ouvrir le dossier** ou **Suivant** pour tout réinitialiser.

Les fichiers sont classés automatiquement dans :
- `Bureau/ISSA Downloader/mp4`
- `Bureau/ISSA Downloader/mp3`

## Exécutable Windows autonome

La compilation `ISSA-onefile.spec` intègre FFmpeg, ffprobe, yt-dlp et Deno
dans un **unique ISSA.exe**. Aucun dossier `_internal` n'est nécessaire.
Au démarrage, PyInstaller extrait temporairement ses composants. Cela peut
ralentir le premier lancement et nécessiter un peu d'espace libre.

Pour compiler localement sur Windows :

```powershell
python -m pip install -r requirements-build.txt
python tools/generate_brand.py
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --clean ISSA-onefile.spec
```

Le fichier obtenu est `dist/ISSA.exe`. Le workflow **ISSA v3 Windows EXE**
produit le même fichier téléchargeable sous `ISSA-v3-FR-EXE`.

Note : le téléchargement de vidéos est limité aux contenus et usages autorisés.
La réussite du build ne garantit pas la disponibilité de toutes les vidéos,
car les règles des sites et les extracteurs peuvent évoluer.
