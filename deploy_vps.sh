#!/bin/bash
# ================================================================
# deploy_vps.sh — Instala o bot em um VPS Ubuntu (Oracle Free Tier)
# Uso: bash deploy_vps.sh
# ================================================================

set -e

echo "🚀 Shopee Affiliate Bot — Setup VPS"
echo "===================================="

# 1. Atualiza sistema
echo "📦 Atualizando sistema..."
sudo apt-get update -qq
sudo apt-get install -y python3.11 python3-pip git wget curl unzip xvfb

# 2. Clona ou atualiza repositório
if [ -d "shopee-affiliate-bot" ]; then
    echo "🔄 Atualizando repositório..."
    cd shopee-affiliate-bot
    git pull
else
    echo "📥 Clonando repositório..."
    git clone https://github.com/SEU_USUARIO/shopee-affiliate-bot.git
    cd shopee-affiliate-bot
fi

# 3. Instala dependências Python
echo "🐍 Instalando dependências Python..."
pip3 install -r requirements.txt

# 4. Instala Playwright + Chromium
echo "🎭 Instalando Playwright Chromium..."
playwright install chromium
playwright install-deps chromium

# 5. Cria .env se não existir
if [ ! -f ".env" ]; then
    echo "⚙️ Criando .env..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANTE: Edite o arquivo .env com suas credenciais:"
    echo "   nano .env"
    echo ""
fi

# 6. Cria pastas necessárias
mkdir -p data/videos logs

# 7. Configura crontab para rodar automaticamente
echo "⏰ Configurando crontab (09:00, 13:00, 20:00 BRT)..."
CRONFILE=$(crontab -l 2>/dev/null || echo "")
BOT_DIR="$(pwd)"

# Remove jobs antigos do bot
CRONFILE=$(echo "$CRONFILE" | grep -v "shopee-affiliate-bot")

# Adiciona novos jobs
CRONFILE="$CRONFILE
0 12 * * * cd $BOT_DIR && python3 main.py >> logs/cron.log 2>&1
0 16 * * * cd $BOT_DIR && python3 main.py >> logs/cron.log 2>&1
0 23 * * * cd $BOT_DIR && python3 main.py >> logs/cron.log 2>&1"

echo "$CRONFILE" | crontab -
echo "✅ Crontab configurado!"

# 8. Configura serviço systemd para o dashboard (opcional)
echo "📊 Configurando serviço do dashboard Streamlit..."
sudo tee /etc/systemd/system/shopee-dashboard.service > /dev/null << EOF
[Unit]
Description=Shopee Affiliate Dashboard
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
ExecStart=/usr/local/bin/streamlit run dashboard/app.py --server.port 8501 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable shopee-dashboard
sudo systemctl start shopee-dashboard

echo ""
echo "✅ INSTALAÇÃO COMPLETA!"
echo "========================"
echo "📊 Dashboard: http://$(curl -s ifconfig.me):8501"
echo "📝 Logs: tail -f $BOT_DIR/logs/cron.log"
echo "⚙️  Editar config: nano $BOT_DIR/.env"
echo ""
echo "💡 Para abrir firewall porta 8501:"
echo "   sudo ufw allow 8501"
