#!/bin/bash
set -e

echo "🔧 Installation des dépendances..."
if [ -n "${VERCEL:-}" ]; then
  # Image Vercel : Python géré par uv (PEP 668 refuse pip système)
  uv pip install --system -r requirements.txt \
    || python -m pip install --break-system-packages -r requirements.txt
else
  pip install -r requirements.txt
fi

echo "🗃️ Exécution des migrations (base de production)..."
python manage.py migrate --noinput

echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "🚚 Export vers staticfiles_build/ (sortie de build Vercel)..."
rm -rf staticfiles_build
mkdir -p staticfiles_build
cp -rf staticfiles/. staticfiles_build/

echo "✅ Build terminé avec succès !"