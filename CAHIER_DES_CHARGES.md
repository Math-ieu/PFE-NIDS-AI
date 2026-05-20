# 📘 Cahier des Charges : Système de Détection d'Intrusion (NIDS-AI)

## 1. Introduction du Projet

### 1.1 Contexte
Le projet s'inscrit dans le cadre d'un Stage de Fin d'Études (PFE). Face à l'évolution constante des cyber-menaces, les solutions traditionnelles basées sur les signatures deviennent insuffisantes. L'objectif est d'exploiter la puissance du **Deep Learning** pour créer un système capable d'apprendre les comportements réseau normaux et de détecter les anomalies avec une grande précision.

### 1.2 Problématique
Comment concevoir un système de détection d'intrusion qui soit à la fois :
- **Adaptatif** : Capable de détecter des attaques inconnues (Zero-day).
- **Précis** : Minimisant les faux positifs et négatifs.
- **Performant** : Capable de traiter les flux de données en temps réel ou quasi-réel.
- **Scalable** : Déployable dans des infrastructures Cloud modernes.

---

## 2. Objectifs Détaillés

### 2.1 Analyse et Modélisation
- **Utilisation du dataset CICIDS 2017** : Ce jeu de données propose un ensemble complet comprenant des comportements normaux (Benign) et des attaques simulées (DDoS, Brute Force, Scanning, etc.) dans un environnement réseau réaliste.
- Prétraitement des données : Nettoyage, normalisation, encodage et sélection de caractéristiques (extraction de features de flux).
- Implémentation de plusieurs architectures Deep Learning (MLP, CNN, RNN/LSTM, Transformers, Autoencoders).
- Évaluation comparative basée sur des métriques standard (Accuracy, Precision, Recall, F1, AUC-ROC).

### 2.2 Mise en Situation (Cyberrange AWS)
- Mise en place d'une infrastructure cloud simulant un réseau d'entreprise.
- Déploiement du modèle sélectionné (**Attention MLP**) sur un nœud d'analyse.
- Simulation d'attaques (DDoS, Brute Force, Scanning) depuis un nœud attaquant.
- Validation de la capacité du modèle à détecter ces attaques en conditions réelles.

---

## 3. Spécifications Techniques

### 3.1 Environnement de Développement
- **Langage** : Python 3.10+
- **Bibliothèques ML** : TensorFlow 2.x, Keras, PyTorch (optionnel).
- **Traitement de données** : Pandas, Scikit-learn, NumPy.
- **Visualisation** : Matplotlib, Seaborn.

### 3.2 Modèles Implémentés et Résultats
Onze modèles ont été entraînés. Les résultats montrent que le modèle **Attention MLP** offre le meilleur compromis performance/temps d'entraînement, tandis que le **CNN-LSTM** offre une robustesse temporelle intéressante.

---

## 4. Architecture de la Solution AWS (Cyberrange)

L'infrastructure sur AWS est conçue pour être hautement disponible et découplée :

| Composant | Rôle | Technologie |
| :--- | :--- | :--- |
| **Zone d'Attaque** | Simulation locale (VMware) envoyant du trafic via Internet. | Kali Linux |
| **VPC Cible** | Héberge les serveurs Web, SSH et RDS cibles. | Amazon VPC |
| **Sonde (Mirroring)** | Capture le trafic et extrait les features de flux. | Sonde passive via NFStreamer |
| **Queue (SQS)** | Bufferise les flux extraits pour l'inférence. | Amazon SQS |
| **Prétraitement** | Normalisation des données à la volée. | AWS Lambda |
| **Moteur d'Inférence** | Prédiction en temps réel (< 5ms). | EC2 + FastAPI (Attention MLP) |
| **Alerting** | Notification immédiate en cas d'attaque. | Amazon SNS (Slack/Email) |
| **Dashboard SOC** | Visualisation et monitoring interactif des menaces. | ReactJS (Vite) + Nginx |

### Flux de Données détaillé :
1. **Attaque** : L'attaquant (Kali) lance des payloads via une IP publique/VPN.
2. **Mirroring** : Le trafic est dupliqué au niveau du VPC AWS sans impact sur la cible.
3. **Extraction** : La sonde convertit les paquets PCAP en flux JSON caractéristiques.
4. **Pipeline** : SQS → Lambda (Scaling) → EC2 Inférence.
5. **Alerte** : Si `classe != BENIGN` et `conf >= 70%`, une alerte SNS est déclenchée.
6. **SOC** : Les alertes sont stockées dans DynamoDB et diffusées en temps réel sur le tableau de bord React via WebSockets.

---

## 5. Livrables Attendus
- Code source complet (entraînement + inférence).
- Modèles pré-entraînés (fichiers `.h5` ou `.pth`).
- Rapport de performance comparatif.
- Rapport de déploiement Cloud (Infrastructure as Code ou Guide de config).
- Mémoire de stage final.

---

## 6. Planning Révisionnel
1. **Phase 1 : Recherche & Data Preparation** (Terminé)
2. **Phase 2 : Développement & Entraînement des Modèles** (Terminé)
3. **Phase 3 : Évaluation & Sélection du Meilleur Modèle** (Terminé)
4. **Phase 4 : Conception de l'Architecture AWS** (Terminé)
5. **Phase 5 : Déploiement & Tests en Conditions Réelles** (Terminé)
6. **Phase 6 : Rédaction du Mémoire** (En cours)
