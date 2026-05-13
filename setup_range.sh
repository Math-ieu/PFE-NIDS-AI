#!/bin/bash

# Configuration
IDS_IP="34.250.74.247"
VICTIM_IP="54.72.207.235"
SOC_IP="108.131.195.208"
KEY="terraform/nids-pfe-key.pem"
SQS_URL="https://sqs.eu-west-1.amazonaws.com/747208289816/nids-flow-queue"

echo "[*] Déploiement du Cyberrange en cours..."

# 1. Configuration de l'IDS
echo "[*] Configuration de l'IDS ($IDS_IP)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IDS_IP "sudo mkdir -p /opt/nids && sudo chown ubuntu:ubuntu /opt/nids"

echo "  [>] Transfert des fichiers..."
scp -i $KEY -o StrictHostKeyChecking=no attention_mlp_best.pth models.py prepocessor.py ansible/ids_engine.py ubuntu@$IDS_IP:/opt/nids/

echo "  [>] Installation des dépendances (cela peut prendre quelques minutes)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IDS_IP << EOF
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libpcap-dev
pip3 install torch nfstream boto3 pandas numpy scapy
EOF

echo "  [>] Configuration du service NIDS..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IDS_IP << EOF
sudo bash -c 'cat << SERVICE > /etc/systemd/system/nids.service
[Unit]
Description=NIDS AI Inference Engine
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/nids
ExecStart=/usr/bin/python3 /opt/nids/ids_engine.py
Restart=always
Environment="SQS_QUEUE_URL=$SQS_URL"

[Install]
WantedBy=multi-user.target
SERVICE'
sudo systemctl daemon-reload
sudo systemctl enable nids
sudo systemctl restart nids
EOF

# 2. Configuration de la Victime
echo "[*] Configuration de la Victime ($VICTIM_IP)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$VICTIM_IP "sudo systemctl start apache2"

echo "[+] Déploiement terminé !"
echo "--------------------------------------------------"
echo "Pour tester la détection :"
echo "1. Connectez-vous à l'IDS pour voir les logs : ssh -i $KEY ubuntu@$IDS_IP 'sudo journalctl -u nids -f'"
echo "2. Lancez une attaque depuis votre machine : python3 scripts/attack_sim.py $VICTIM_IP scan'"
echo "--------------------------------------------------"
