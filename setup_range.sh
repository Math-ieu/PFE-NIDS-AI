#!/bin/bash

# Target Key
KEY="terraform/nids-pfe-key.pem"

echo "[*] Déploiement du Cyberrange en cours..."

# 1. Résolution dynamique des adresses IP depuis Terraform
if [ -d "terraform" ]; then
  echo "[*] Récupération des adresses IP depuis Terraform..."
  IDS_IP=$(terraform -chdir=terraform output -raw ids_public_ip 2>/dev/null)
  SOC_IP=$(terraform -chdir=terraform output -raw soc_public_ip 2>/dev/null)
  KALI_IP=$(terraform -chdir=terraform output -raw kali_public_ip 2>/dev/null)
  SQS_URL=$(terraform -chdir=terraform output -raw sqs_queue_url 2>/dev/null)
  
  # Extraction des IPs des victimes
  VICTIM_WEB_IP=$(terraform -chdir=terraform output -json victim_public_ips 2>/dev/null | jq -r '.web' 2>/dev/null || terraform -chdir=terraform output -json victim_public_ips 2>/dev/null | grep -oP '"web":\s*"\K[^"]+')
  VICTIM_DB_IP=$(terraform -chdir=terraform output -json victim_public_ips 2>/dev/null | jq -r '.db' 2>/dev/null || terraform -chdir=terraform output -json victim_public_ips 2>/dev/null | grep -oP '"db":\s*"\K[^"]+')
  VICTIM_FILE_IP=$(terraform -chdir=terraform output -json victim_public_ips 2>/dev/null | jq -r '.file' 2>/dev/null || terraform -chdir=terraform output -json victim_public_ips 2>/dev/null | grep -oP '"file":\s*"\K[^"]+')
fi

# Valeurs de repli par défaut si Terraform n'est pas initialisé ou en cas d'erreur
IDS_IP=${IDS_IP:-"34.250.74.247"}
SOC_IP=${SOC_IP:-"108.131.195.208"}
KALI_IP=${KALI_IP:-"54.220.100.100"}
SQS_URL=${SQS_URL:-"https://sqs.eu-west-1.amazonaws.com/747208289816/nids-flow-queue"}
VICTIM_WEB_IP=${VICTIM_WEB_IP:-"54.72.207.235"}
VICTIM_DB_IP=${VICTIM_DB_IP:-"54.72.207.236"}
VICTIM_FILE_IP=${VICTIM_FILE_IP:-"54.72.207.237"}

echo "--------------------------------------------------"
echo "[-] IDS IP:        $IDS_IP"
echo "[-] SOC IP:        $SOC_IP"
echo "[-] KALI IP:       $KALI_IP"
echo "[-] Victim-Web IP: $VICTIM_WEB_IP"
echo "[-] Victim-DB IP:  $VICTIM_DB_IP"
echo "[-] Victim-File IP:$VICTIM_FILE_IP"
echo "[-] SQS URL:       $SQS_URL"
echo "--------------------------------------------------"

# 2. Génération dynamique de l'inventaire Ansible
echo "[*] Génération de l'inventaire ansible/inventory.ini..."
cat << INVENTORY > ansible/inventory.ini
[ids]
ids_node ansible_host=$IDS_IP

[victims]
victim-web ansible_host=$VICTIM_WEB_IP
victim-db ansible_host=$VICTIM_DB_IP
victim-file ansible_host=$VICTIM_FILE_IP

[soc]
soc_node ansible_host=$SOC_IP

[kali]
kali-attack ansible_host=$KALI_IP ansible_user=kali

[all:vars]
ansible_user=ubuntu
ansible_ssh_private_key_file=terraform/nids-pfe-key.pem
ansible_ssh_common_args='-o StrictHostKeyChecking=no'
INVENTORY
echo "[+] Inventaire Ansible mis à jour."

# 3. Configuration de l'IDS
echo "[*] Configuration de l'IDS ($IDS_IP)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IDS_IP "sudo mkdir -p /opt/nids && sudo chown ubuntu:ubuntu /opt/nids"

echo "  [>] Transfert des fichiers du moteur NIDS AI..."
scp -i $KEY -o StrictHostKeyChecking=no attention_mlp_best.pth models.py prepocessor.py ansible/ids_engine.py ubuntu@$IDS_IP:/opt/nids/

echo "  [>] Installation des dépendances NIDS AI (cela peut prendre quelques minutes)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$IDS_IP << EOF
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libpcap-dev
pip3 install torch nfstream boto3 pandas numpy scapy
EOF

echo "  [>] Configuration du service Systemd NIDS..."
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

# 4. Configuration des Victimes
echo "[*] Configuration des serveurs Victimes..."

echo "  [>] Redémarrage des services sur Victim-Web ($VICTIM_WEB_IP)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$VICTIM_WEB_IP "sudo systemctl restart apache2" 2>/dev/null || echo "    [!] Erreur ou service indisponible sur Victim-Web"

echo "  [>] Redémarrage des services sur Victim-DB ($VICTIM_DB_IP)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$VICTIM_DB_IP "sudo systemctl restart mariadb redis-server" 2>/dev/null || echo "    [!] Erreur ou service indisponible sur Victim-DB"

echo "  [>] Redémarrage des services sur Victim-File ($VICTIM_FILE_IP)..."
ssh -i $KEY -o StrictHostKeyChecking=no ubuntu@$VICTIM_FILE_IP "sudo systemctl restart smbd vsftpd" 2>/dev/null || echo "    [!] Erreur ou service indisponible sur Victim-File"

echo "[+] Déploiement terminé avec succès !"
echo "--------------------------------------------------"
echo "Pour tester le système :"
echo "1. Connectez-vous à la machine d'attaque Kali Linux :"
echo "   - SSH : ssh -i $KEY kali@$KALI_IP"
echo "   - RDP (Interface Graphique) : Connectez-vous à $KALI_IP:3389 (utilisateur: 'kali', mot de passe: 'KaliRangePassword123!')"
echo "2. Effectuez des scans ou des attaques contre l'une des victimes :"
echo "   - Victim-Web: $VICTIM_WEB_IP"
echo "   - Victim-DB:  $VICTIM_DB_IP"
echo "   - Victim-File:$VICTIM_FILE_IP"
echo "3. Suivez la détection en direct sur le SOC Dashboard ($SOC_IP) ou sur l'IDS : "
echo "   ssh -i $KEY ubuntu@$IDS_IP 'sudo journalctl -u nids -f'"
echo "--------------------------------------------------"
