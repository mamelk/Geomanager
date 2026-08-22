#!/bin/bash
# ═══════════════════════════════════════════════
#  Démarrer ngrok pour les callbacks MaishaPay
# ═══════════════════════════════════════════════

echo "🚀 Démarrage de ngrok sur le port 8000..."
echo ""

# Lancer ngrok en arrière-plan
./ngrok.exe http 8000 &
NGROK_PID=$!

# Attendre que ngrok soit prêt
sleep 4

# Récupérer l'URL publique
NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels | python -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data['tunnels'][0]['public_url'])
except:
    print('')
")

if [ -z "$NGROK_URL" ]; then
    echo "❌ Impossible de récupérer l'URL ngrok."
    echo "   Ouvrez http://127.0.0.1:4040 dans votre navigateur."
    exit 1
fi

CALLBACK_URL="${NGROK_URL}/courses/paiement/callback/"

echo "✅ ngrok actif !"
echo ""
echo "════════════════════════════════════════════════"
echo "  URL publique : $NGROK_URL"
echo "  Callback URL : $CALLBACK_URL"
echo "════════════════════════════════════════════════"
echo ""

# Mettre à jour le .env
sed -i "s|MAISHAPAY_CALLBACK_URL=.*|MAISHAPAY_CALLBACK_URL=${CALLBACK_URL}|" .env
echo "📝 .env mis à jour avec la callback URL ngrok."
echo ""
echo "📋 Copiez cette URL dans votre dashboard MaishaPay si besoin :"
echo "   $CALLBACK_URL"
echo ""
echo "🌐 Dashboard ngrok : http://127.0.0.1:4040"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter ngrok."
wait $NGROK_PID
