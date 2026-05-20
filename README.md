# PFE-NIDS-AI : Deep Learning-based Network Intrusion Detection System

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-Cyberrange-orange.svg)](https://aws.amazon.com/)
[![Terraform](https://img.shields.io/badge/IaC-Terraform-623CE4.svg)](https://www.terraform.io/)

## Présentation du Projet

Ce projet est un **Système de Détection d'Intrusion Réseau (NIDS)** développé dans le cadre d'un Projet de Fin d'Études (PFE). Il utilise des techniques avancées de **Deep Learning** pour identifier et classifier les cyber-attaques en temps réel en analysant les motifs du trafic réseau.

Contrairement aux systèmes IDS traditionnels basés sur des signatures, ce système utilise l'analyse comportementale pour détecter les menaces connues ainsi que les attaques sophistiquées de type **Zero-day**.

---

## Menaces Détectées

Le système est entraîné pour identifier avec précision les vecteurs d'attaque suivants :
- **DDoS / DoS** : GoldenEye, Hulk, Slowloris, etc.
- **Scanning** : Port Scanning (Nmap), Vulnerability Scanning.
- **Brute Force** : SSH, FTP (via Hydra).
- **Web Attacks** : SQL Injection, XSS, Infiltration.
- **Botnets & Malware** : Détection des communications C2.

---

- **Détection Multi-Architecture** : Évaluation de 11 modèles de Deep Learning (Attention MLP, CNN-LSTM, Transformers, etc.).
- **Temps Réel** : Pipeline d'inférence haute performance avec une latence < 5ms par flux.
- **Cloud Native** : Infrastructure AWS industrialisée via **Terraform** (IaC).
- **Dashboard Premium** : Interface SOC interactive en **ReactJS + Vite** (design Glassmorphism, thèmes **Dark / Light**, menu repliable avec persistance locale, rafraîchissement des graphes optimisé à 10s et filtrage par date ultra-réactif sur tous les flux en direct et historiques).
- **Mirroring Passif** : Utilisation d'AWS VPC Traffic Mirroring pour analyser le trafic sans impact sur les performances des cibles.
- **Automated Lab** : Simulation d'attaques automatisée via scripts Python (Scapy) et Kali Linux.

---

## Performance des Modèles

Le projet a comparé **11 architectures différentes** sur le dataset **CICIDS 2017**.

| Modèle | Précision (%) | F1-Score (%) | AUC-ROC | Temps d'Entraînement |
| :--- | :---: | :---: | :---: | :---: |
| **Attention MLP** | **98.28** | **98.29** | **0.9995** | **Rapide (258s)** |
| **CNN-LSTM** | 98.14 | 97.99 | 0.9995 | Lent (3502s) |
| **ResNet1D** | 98.14 | 98.12 | 0.9995 | Moyen (639s) |
| BiLSTM | 97.92 | 97.94 | 0.9992 | Lent (2227s) |
| Transformers | 97.58 | 97.47 | 0.9991 | Très Lent (3213s) |

> [!TIP]
> Le modèle **Attention MLP** a été sélectionné pour le déploiement final en raison de son excellent compromis entre précision chirurgicale et efficacité de calcul.

---

## Architecture du Système

L'infrastructure est entièrement déployée sur **AWS (Region: eu-west-1)** et utilise une approche hybride associant des instances EC2 spécialisées et un pipeline serverless asynchrone pour la persistance des alertes.

```mermaid
flowchart TB
    subgraph ATTACK["Zone d'Attaque (AWS Externe/Interne)"]
        KALI["<b>Kali Linux Attack Machine</b><br/>Interface GUI/RDP (XFCE + XRDP)<br/>Nmap / Hping3 / Scapy"]
    end

    subgraph AWS["Infrastructure AWS (Region: eu-west-1)"]
        direction TB

        subgraph VPC["VPC Security Zone (10.0.0.0/16)"]
            direction TB
            subgraph VICTIMS["Cibles du Cyberrange (Subnet Public)"]
                V_WEB["<b>Victim-Web</b><br/>(10.0.1.232)<br/>Apache + PHP"]
                V_DB["<b>Victim-DB</b><br/>(10.0.1.180)<br/>MariaDB + Redis"]
                V_FILE["<b>Victim-File</b><br/>(10.0.1.244)<br/>Samba + vsftpd (FTP)"]
            end

            IDS["<b>IDS-Node</b><br/>VXLAN vxlan0 (VNI 100)<br/>NFStream + PyTorch IA"]
            SOC_SRV["<b>SOC-Dashboard Node</b><br/>Nginx (Frontend Port 80)<br/>FastAPI + WebSockets (Port 8001)"]
        end

        subgraph PIPELINE["Pipeline de Données Asynchrone"]
            SQS[("AWS SQS<br/>Alert Queue")]
            LAMBDA["AWS Lambda<br/>Data Normalization"]
            DYNAMO[("AWS DynamoDB<br/>Alerts Storage")]
        end

        S3[("S3 Bucket<br/>AI Models (.pth)")]
    end

    %% Network & Attack Flows
    KALI -->|Attaques Réseau| V_WEB
    KALI -->|Attaques Réseau| V_DB
    KALI -->|Attaques Réseau| V_FILE
    
    %% Traffic Mirroring Flows
    V_WEB -.->|VPC Traffic Mirroring| IDS
    V_DB -.->|VPC Traffic Mirroring| IDS
    V_FILE -.->|VPC Traffic Mirroring| IDS

    %% Data Pipeline Flow
    IDS -->|JSON Flow Features| SQS
    SQS --> LAMBDA
    LAMBDA --> DYNAMO
    DYNAMO <-->|Flux Temps Réel| SOC_SRV
    SOC_SRV -->|WebSockets Push| UI["Glassmorphic SOC Dashboard UI"]

    %% Styles
    style V_WEB fill:#ffe5e5,stroke:#ff3e60,stroke-width:2px
    style V_DB fill:#ffe5e5,stroke:#ff3e60,stroke-width:2px
    style V_FILE fill:#ffe5e5,stroke:#ff3e60,stroke-width:2px
    style IDS fill:#e6f9ff,stroke:#00d4ff,stroke-width:2px
    style SOC_SRV fill:#e6fff4,stroke:#00ff94,stroke-width:2px
    style KALI fill:#f5f0ff,stroke:#7000ff,stroke-width:2px
    style PIPELINE fill:#f5f5f5,stroke:#333
    style UI fill:#fffbeb,stroke:#ffcc00,stroke-width:2px
```


---

## Pipeline de Détection et d'Alerte Étape par Étape

Le diagramme de séquence ci-dessous illustre le parcours d'un flux de données réseau, depuis le déclenchement d'une cyber-attaque sur la zone d'entraînement jusqu'à sa visualisation en temps réel sur le tableau de bord du SOC :

```mermaid
sequenceDiagram
    autonumber
    actor Attaquant as 💻 Kali Linux (Attaquant)
    participant Victime as 🖥️ Cible (Victim Node)
    participant Mirror as ☁️ AWS VPC (Traffic Mirroring)
    participant Sonde as 🔍 IDS-Node (NFStreamer)
    participant IA as 🧠 Attention MLP (PyTorch)
    participant Dynamo as 🗄️ AWS DynamoDB (NIDS-Alerts)
    participant SQS as ✉️ AWS SQS (flow_queue)
    participant Lambda as ⚡ AWS Lambda (Prep)
    participant Back as ⚙️ SOC Backend (FastAPI)
    actor Analyste as 📊 SOC Dashboard (React UI)

    Note over Attaquant, Victime: Étape 1 : Attaque & Trafic Réseau
    Attaquant->>Victime: Envoi de Trafic Malveillant (DDoS, Scan, Brute Force)
    
    Note over Victime, Mirror: Étape 2 : Captation (Zero-Impact)
    Mirror->>Victime: Duplication passive des paquets suspects
    Mirror->>Sonde: Encapsulation VXLAN (Port 4789) vers l'interface vxlan0
    
    Note over Sonde, IA: Étape 3 & 4 : Analyse & Inférence de l'IA
    Sonde->>Sonde: Décapsulation VXLAN & Agrégation par flux réseau
    Sonde->>IA: Extraction des 77 caractéristiques (Features) du flux
    IA->>IA: Classification par le modèle de Deep Learning
    Note over IA: Si Attaque détectée & Confiance >= 40%
    
    Note over IA, Dynamo: Étape 5 : Routage & Stockage des Alertes
    IA->>Dynamo: Sauvegarde immédiate de l'Alerte enrichie
    IA->>SQS: Bufferisation du JSON d'alerte pour les audits
    SQS->>Lambda: Déclenchement automatique pour pré-traitement / archivage S3
    
    Note over Dynamo, Analyste: Étape 6 & 7 : Diffusion & Visualisation SOC
    Back->>Dynamo: Polling et enrichissement de l'IP en Nom de Machine
    Back->>Analyste: Diffusion en temps réel via WebSockets (Port 8001)
    Analyste->>Analyste: Affichage instantané, alerte sonore, mise à jour des KPIs
```

---

## Stack Technique

- **Intelligence Artificielle** : PyTorch, Scikit-learn, Pandas, NFStreamer.
- **Backend & API** : FastAPI, Pydantic, WebSockets.
- **Frontend** : ReactJS (Vite + Component-driven design), CSS3 Glassmorphic Cyberpunk, Lucide Icons, Chart.js.
- **Infrastructure** : AWS (EC2, Lambda, SQS, DynamoDB, S3, VPC Mirroring).
- **IaC & DevOps** : Terraform, Ansible, Git.

---

## Installation & Déploiement

### 1. Prérequis
- Python 3.10+
- Node.js & npm (pour le développement/build frontend)
- Compte AWS configuré
- Terraform & Ansible installés

### 2. Déploiement Cloud (Terraform & Ansible)
```bash
# 1. Déployer l'infrastructure sur AWS
cd terraform
terraform init
terraform apply -auto-approve

# 2. Configurer et orchestrer le Cyberrange (depuis la racine)
cd ..
./setup_range.sh
```
Ce script `setup_range.sh` génère l'inventaire Ansible de manière dynamique et applique le playbook `ansible/playbook.yml` pour provisionner et démarrer tous les services ainsi que le NIDS.

### 3. Lancer le Dashboard Localement (Mode Debug)
```bash
# Dans un premier terminal (Backend FastAPI) :
cd soc_dashboard/backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py

# Dans un second terminal (Frontend React + Vite) :
cd soc_dashboard/frontend
npm install
npm run dev
```

---

## Documentation Complète

Pour plus de détails sur les spécifications techniques et les choix de conception, consultez le [Cahier des Charges](CAHIER_DES_CHARGES.md).

---

## Auteur
- **Mathieu** - Étudiant en Ingénierie Cyber-sécurité / IA.

---
*Ce projet a été réalisé dans le cadre d'un Stage de Fin d'Études (PFE).*
