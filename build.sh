#!/bin/bash
set -e

echo "🔧 Installation des dépendances..."
pip install -r requirements.txt

echo "🗃️ Exécution des migrations (base de production)..."
python manage.py migrate --noinput

echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

echo "🚚 Export vers staticfiles_build/ (sortie de build Vercel)..."
rm -rf staticfiles_build
mkdir -p staticfiles_build
cp -rf staticfiles/. staticfiles_build/

echo "✅ Build terminé avec succès !"