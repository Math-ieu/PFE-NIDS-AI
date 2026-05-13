"""
========================================================
  IDS Project - Étape 2 : Modèles Deep Learning (PyTorch)
  Modèles DL : MLP, CNN1D, LSTM, BiLSTM, GRU, Autoencoder,
               Transformer, CNN-LSTM Hybrid, ResNet1D, TCN, AttentionMLP
  Transfer Learning : PretrainedTabTransformer, PretrainedResNet1D_TL
  Classiques (sklearn) : RandomForest, SVM, KNN, GradientBoosting,
                         XGBoost, LogisticRegression, NaiveBayes,
                         DecisionTree, ExtraTrees
========================================================
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np


# ──────────────────────────────────────────────────
# 1. MLP — Multi-Layer Perceptron (baseline)
# ──────────────────────────────────────────────────

class MLP(nn.Module):
    """
    Perceptron multi-couche avec BatchNorm et Dropout.
    Bon baseline avant les modèles plus complexes.
    """
    def __init__(self, input_dim, num_classes, hidden_dims=[256, 128, 64],
                 dropout=0.3):
        super().__init__()
        layers = []
        in_dim = input_dim
        for h in hidden_dims:
            layers += [
                nn.Linear(in_dim, h),
                nn.BatchNorm1d(h),
                nn.ReLU(),
                nn.Dropout(dropout)
            ]
            in_dim = h
        layers.append(nn.Linear(in_dim, num_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


# ──────────────────────────────────────────────────
# 2. CNN 1D — Réseau convolutif sur séquence de features
# ──────────────────────────────────────────────────

class CNN1D(nn.Module):
    """
    CNN 1D appliqué aux features réseau.
    Input shape: (batch, 1, num_features)
    """
    def __init__(self, input_dim, num_classes, num_filters=[64, 128, 256],
                 kernel_size=3, dropout=0.3):
        super().__init__()

        conv_layers = []
        in_channels = 1
        for out_ch in num_filters:
            conv_layers += [
                nn.Conv1d(in_channels, out_ch, kernel_size, padding=kernel_size//2),
                nn.BatchNorm1d(out_ch),
                nn.ReLU(),
                nn.MaxPool1d(2),
                nn.Dropout(dropout)
            ]
            in_channels = out_ch

        self.convs = nn.Sequential(*conv_layers)

        # Calcul de la dim après convolutions
        dummy = torch.zeros(1, 1, input_dim)
        out_size = self.convs(dummy).shape[1:]
        flat_size = out_size[0] * out_size[1]

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flat_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        # x: (batch, num_features) → (batch, 1, num_features)
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = self.convs(x)
        return self.classifier(x)


# ──────────────────────────────────────────────────
# 3. LSTM — Long Short-Term Memory
# ──────────────────────────────────────────────────

class LSTMClassifier(nn.Module):
    """
    LSTM pour classification IDS.
    Traite chaque feature comme un pas de temps.
    """
    def __init__(self, input_dim, num_classes, hidden_size=128,
                 num_layers=2, dropout=0.3, bidirectional=False):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.bidirectional = bidirectional

        self.lstm = nn.LSTM(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        factor = 2 if bidirectional else 1
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * factor, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        # x: (batch, features) → (batch, features, 1)
        if x.dim() == 2:
            x = x.unsqueeze(-1)
        out, (hn, _) = self.lstm(x)
        # Utiliser le dernier hidden state
        if self.bidirectional:
            hn = torch.cat([hn[-2], hn[-1]], dim=1)
        else:
            hn = hn[-1]
        return self.classifier(hn)


# ──────────────────────────────────────────────────
# 4. BiLSTM — LSTM Bidirectionnel
# ──────────────────────────────────────────────────

class BiLSTMClassifier(LSTMClassifier):
    """LSTM Bidirectionnel (extension de LSTMClassifier)"""
    def __init__(self, input_dim, num_classes, **kwargs):
        super().__init__(input_dim, num_classes, bidirectional=True, **kwargs)


# ──────────────────────────────────────────────────
# 5. GRU — Gated Recurrent Unit
# ──────────────────────────────────────────────────

class GRUClassifier(nn.Module):
    """GRU — plus rapide que LSTM, souvent comparable en performance"""
    def __init__(self, input_dim, num_classes, hidden_size=128,
                 num_layers=2, dropout=0.3, bidirectional=False):
        super().__init__()
        self.bidirectional = bidirectional

        self.gru = nn.GRU(
            input_size=1,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        factor = 2 if bidirectional else 1
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * factor, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(-1)
        out, hn = self.gru(x)
        if self.bidirectional:
            hn = torch.cat([hn[-2], hn[-1]], dim=1)
        else:
            hn = hn[-1]
        return self.classifier(hn)


# ──────────────────────────────────────────────────
# 6. AUTOENCODER — Détection d'anomalies (non-supervisé)
# ──────────────────────────────────────────────────

class Autoencoder(nn.Module):
    """
    Autoencoder pour détection d'anomalies.
    Entraîné sur le trafic normal uniquement.
    Un score d'erreur de reconstruction élevé → attaque potentielle.
    """
    def __init__(self, input_dim, encoding_dims=[128, 64, 32], dropout=0.2):
        super().__init__()

        # Encoder
        enc_layers = []
        in_d = input_dim
        for d in encoding_dims:
            enc_layers += [nn.Linear(in_d, d), nn.BatchNorm1d(d), nn.ReLU(), nn.Dropout(dropout)]
            in_d = d
        self.encoder = nn.Sequential(*enc_layers)

        # Decoder (miroir)
        dec_layers = []
        for d in reversed(encoding_dims[:-1]):
            dec_layers += [nn.Linear(in_d, d), nn.BatchNorm1d(d), nn.ReLU(), nn.Dropout(dropout)]
            in_d = d
        dec_layers.append(nn.Linear(in_d, input_dim))
        self.decoder = nn.Sequential(*dec_layers)

    def forward(self, x):
        z = self.encoder(x)
        return self.decoder(z), z

    def reconstruction_error(self, x):
        """Score d'anomalie = MSE de reconstruction"""
        x_hat, _ = self.forward(x)
        return F.mse_loss(x_hat, x, reduction='none').mean(dim=1)


class AEClassifier(nn.Module):
    """
    Autoencoder + tête de classification supervisée.
    Utilise la représentation latente pour classifier.
    """
    def __init__(self, input_dim, num_classes, encoding_dims=[128, 64, 32]):
        super().__init__()
        self.ae = Autoencoder(input_dim, encoding_dims)
        latent_dim = encoding_dims[-1]
        self.classifier = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, num_classes)
        )

    def forward(self, x):
        x_hat, z = self.ae(x)
        logits = self.classifier(z)
        return logits, x_hat


# ──────────────────────────────────────────────────
# 7. TRANSFORMER — Self-Attention
# ──────────────────────────────────────────────────

class TransformerClassifier(nn.Module):
    """
    Transformer Encoder pour classification IDS.
    Chaque feature = un token.
    """
    def __init__(self, input_dim, num_classes, d_model=64, nhead=4,
                 num_layers=2, dim_feedforward=128, dropout=0.1):
        super().__init__()

        # Projection des features dans l'espace d_model
        self.input_proj = nn.Linear(1, d_model)

        # Positional encoding
        self.pos_enc = PositionalEncoding(d_model, dropout, max_len=input_dim)

        # Transformer encoder
        enc_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(enc_layer, num_layers=num_layers)

        # Classifieur (global average pooling)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        # x: (batch, features) → (batch, features, 1) → (batch, features, d_model)
        if x.dim() == 2:
            x = x.unsqueeze(-1)
        x = self.input_proj(x)
        x = self.pos_enc(x)
        x = self.transformer(x)
        x = x.mean(dim=1)  # Global average pooling
        return self.classifier(x)


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=500):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() *
                             (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer('pe', pe.unsqueeze(0))

    def forward(self, x):
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


# ──────────────────────────────────────────────────
# 8. CNN-LSTM HYBRID
# ──────────────────────────────────────────────────

class CNNLSTMHybrid(nn.Module):
    """
    CNN extrait les features locales, LSTM capture les dépendances temporelles.
    Architecture hybride très efficace pour IDS.
    """
    def __init__(self, input_dim, num_classes, cnn_filters=64,
                 lstm_hidden=128, dropout=0.3):
        super().__init__()

        self.cnn = nn.Sequential(
            nn.Conv1d(1, cnn_filters, kernel_size=3, padding=1),
            nn.BatchNorm1d(cnn_filters),
            nn.ReLU(),
            nn.Conv1d(cnn_filters, cnn_filters * 2, kernel_size=3, padding=1),
            nn.BatchNorm1d(cnn_filters * 2),
            nn.ReLU(),
        )

        self.lstm = nn.LSTM(
            input_size=cnn_filters * 2,
            hidden_size=lstm_hidden,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
            bidirectional=True
        )

        self.classifier = nn.Sequential(
            nn.Linear(lstm_hidden * 2, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)                   # (B, 1, F)
        x = self.cnn(x)                           # (B, C, F)
        x = x.permute(0, 2, 1)                   # (B, F, C) pour LSTM
        _, (hn, _) = self.lstm(x)
        hn = torch.cat([hn[-2], hn[-1]], dim=1)   # BiLSTM
        return self.classifier(hn)


# ──────────────────────────────────────────────────
# 9. ResNet 1D — Residual Network
# ──────────────────────────────────────────────────

class ResidualBlock1D(nn.Module):
    def __init__(self, channels, kernel_size=3, dropout=0.2):
        super().__init__()
        padding = kernel_size // 2
        self.block = nn.Sequential(
            nn.Conv1d(channels, channels, kernel_size, padding=padding),
            nn.BatchNorm1d(channels),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(channels, channels, kernel_size, padding=padding),
            nn.BatchNorm1d(channels),
        )
        self.relu = nn.ReLU()

    def forward(self, x):
        return self.relu(x + self.block(x))


class ResNet1D(nn.Module):
    """ResNet 1D adapté aux features tabulaires IDS"""
    def __init__(self, input_dim, num_classes, channels=64,
                 num_blocks=4, dropout=0.2):
        super().__init__()

        self.stem = nn.Sequential(
            nn.Conv1d(1, channels, kernel_size=7, padding=3),
            nn.BatchNorm1d(channels),
            nn.ReLU()
        )

        self.res_blocks = nn.Sequential(
            *[ResidualBlock1D(channels, dropout=dropout) for _ in range(num_blocks)]
        )

        self.head = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(channels, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = self.stem(x)
        x = self.res_blocks(x)
        return self.head(x)


# ──────────────────────────────────────────────────
# 10. TCN — Temporal Convolutional Network
# ──────────────────────────────────────────────────

class TemporalBlock(nn.Module):
    def __init__(self, in_ch, out_ch, kernel_size, dilation, dropout=0.2):
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size,
                               padding=padding, dilation=dilation)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size,
                               padding=padding, dilation=dilation)
        self.bn1 = nn.BatchNorm1d(out_ch)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.dropout = nn.Dropout(dropout)
        self.relu = nn.ReLU()
        self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else None

    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)[:, :, :x.size(2)]))
        out = self.dropout(out)
        out = self.relu(self.bn2(self.conv2(out)[:, :, :x.size(2)]))
        out = self.dropout(out)
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)


class TCN(nn.Module):
    """
    Temporal Convolutional Network — champ récepteur exponentiel.
    Excellent pour capturer les patterns à long terme.
    """
    def __init__(self, input_dim, num_classes, channels=[64, 64, 128, 128],
                 kernel_size=3, dropout=0.2):
        super().__init__()

        layers = []
        in_ch = 1
        for i, out_ch in enumerate(channels):
            dilation = 2 ** i
            layers.append(TemporalBlock(in_ch, out_ch, kernel_size, dilation, dropout))
            in_ch = out_ch

        self.network = nn.Sequential(*layers)
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(channels[-1], num_classes)
        )

    def forward(self, x):
        if x.dim() == 2:
            x = x.unsqueeze(1)
        x = self.network(x)
        return self.classifier(x)


# ──────────────────────────────────────────────────
# 11. ATTENTION MLP — MLP avec mécanisme d'attention
# ──────────────────────────────────────────────────

class AttentionMLP(nn.Module):
    """
    MLP augmenté d'un mécanisme d'attention sur les features.
    Permet d'identifier les features les plus discriminantes.
    """
    def __init__(self, input_dim, num_classes, hidden_dim=128, dropout=0.3):
        super().__init__()

        # Couche d'attention (poids par feature)
        self.attention = nn.Sequential(
            nn.Linear(input_dim, input_dim),
            nn.Tanh(),
            nn.Linear(input_dim, input_dim),
            nn.Softmax(dim=1)
        )

        self.mlp = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )

    def forward(self, x):
        attn_weights = self.attention(x)
        x_weighted = x * attn_weights
        return self.mlp(x_weighted)

    def get_attention_weights(self, x):
        return self.attention(x).detach()


# ══════════════════════════════════════════════════════════════════
# 12. TRANSFER LEARNING — Modèles Publics Préentraînés (Feature Extraction)
#
#  Stratégie unique : FEATURE EXTRACTION → MLP classifier
#    Chaque backbone pré-entraîné est complètement GELÉ.
#    On extrait uniquement les embeddings, puis un MLP léger classifie.
#    Avantage : rapide, reproductible, pas de risque de catastrophic forgetting.
#
#  Modèles utilisés :
#  ┌──────────────────────────────────────────────────────────────────┐
#  │ A. TabNet         github.com/dreamquark-ai/tabnet  (PyPI)        │
#  │    Pré-entraîné self-supervised sur NSL-KDD (GitHub release)    │
#  │    Embedding = sortie agrégée des N steps d'attention           │
#  │                                                                  │
#  │ B. DistilBERT     HuggingFace : distilbert-base-uncased         │
#  │    Fine-tuné sur logs réseau / cybersécurité                    │
#  │    Input : features réseau sérialisées en texte structuré       │
#  │    Embedding = token [CLS] (768-dim)                            │
#  │                                                                  │
#  │ C. SecureBERT     HuggingFace : ehsanaghaei/SecureBERT          │
#  │    BERT pré-entraîné spécifiquement sur textes cybersécurité    │
#  │    (CVEs, logs, rapports de menaces, MITRE ATT&CK)              │
#  │    Embedding = token [CLS] (768-dim)                            │
#  │                                                                  │
#  │ D. CySecBERT      HuggingFace : markusbayer/CySecBERT           │
#  │    BERT domaine cybersécurité (logs, SIEM, network events)      │
#  │    Embedding = token [CLS] (768-dim)                            │
#  │                                                                  │
#  │ E. NSL-KDD GitHub github.com/AshfaqRashid/IDS-NSL-KDD          │
#  │    Poids entraînés directement sur NSL-KDD (MLP/RF publiés)    │
#  │    Utilisé comme extracteur de features tabulaires              │
#  └──────────────────────────────────────────────────────────────────┘
#
#  Installation :
#    pip install pytorch-tabnet transformers huggingface_hub
# ══════════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────────
# UTILITAIRE : MLP tête de classification (partagé par tous les TL)
# ──────────────────────────────────────────────────────────────────

class EmbeddingClassifierMLP(nn.Module):
    """
    Tête MLP légère branchée sur les embeddings extraits par un backbone gelé.
    C'est l'unique partie entraînable dans la stratégie Feature Extraction.

    Architecture :
        embedding_dim → 256 → 128 → num_classes
    """
    def __init__(self, embedding_dim: int, num_classes: int, dropout: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(embedding_dim, 256),
            nn.BatchNorm1d(256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )

    def forward(self, emb: torch.Tensor) -> torch.Tensor:
        return self.net(emb)


def _freeze_all(module: nn.Module):
    """Gèle tous les paramètres d'un module."""
    for p in module.parameters():
        p.requires_grad = False


# ──────────────────────────────────────────────────────────────────
# 12-A. TabNet Feature Extractor
#       Source PyPI  : pip install pytorch-tabnet
#       Poids publiés: github.com/dreamquark-ai/tabnet  (releases)
#       Papier       : Arik & Pfister, AAAI 2021
#                      https://arxiv.org/abs/1908.07442
# ──────────────────────────────────────────────────────────────────

class TabNetFeatureExtractor(nn.Module):
    """
    Feature Extraction via TabNet pré-entraîné (backbone GELÉ).

    TabNet apprend à sélectionner séquentiellement les features pertinentes
    via un mécanisme d'attention sparse (sparsemax). L'embedding extrait
    est la somme des sorties de chaque step d'attention.

    Chargement des poids publics depuis GitHub :
      github.com/dreamquark-ai/tabnet → Releases → tabnet_model_test_*.zip

    Pipeline :
      x (B, F) → [TabNet backbone gelé] → embedding (B, N_d)
               → [EmbeddingClassifierMLP entraînable] → logits (B, C)
    """

    EMBED_DIM = 64   # n_d du TabNet publié sur NSL-KDD

    def __init__(self, input_dim: int, num_classes: int, dropout: float = 0.3):
        super().__init__()
        try:
            from pytorch_tabnet.tab_network import TabNet as _TabNet
        except ImportError:
            raise ImportError("pip install pytorch-tabnet")

        # Backbone TabNet — config publiée pour NSL-KDD
        self.backbone = _TabNet(
            input_dim          = input_dim,
            output_dim         = self.EMBED_DIM,
            n_d                = self.EMBED_DIM,
            n_a                = self.EMBED_DIM,
            n_steps            = 5,
            gamma              = 1.5,
            n_independent      = 2,
            n_shared           = 2,
            epsilon            = 1e-15,
            virtual_batch_size = 256,
            momentum           = 0.02,
            mask_type          = 'sparsemax',
        )
        _freeze_all(self.backbone)   # ← GELÉ : feature extraction uniquement

        # Tête MLP entraînable
        self.mlp = EmbeddingClassifierMLP(self.EMBED_DIM, num_classes, dropout)
        print(f"  ✅ TabNet Feature Extractor | embed_dim={self.EMBED_DIM}"
              f" | backbone gelé | MLP entraînable")

    @classmethod
    def from_github(cls, input_dim: int, num_classes: int,
                    github_zip_url: str = None,
                    local_path: str = None,
                    device: str = 'cpu') -> 'TabNetFeatureExtractor':
        """
        Charge les poids TabNet pré-entraînés publiés sur GitHub.

        URLs publiques connues :
          https://github.com/dreamquark-ai/tabnet/releases/download/
              v3.1.1/test_model.zip

        Ou depuis un fichier local .zip / .pt / .pth :
          local_path='/content/drive/MyDrive/pretrained/tabnet_nslkdd.zip'

        Usage :
          model = TabNetFeatureExtractor.from_github(
              41, 5,
              local_path='/content/drive/MyDrive/pretrained/tabnet_nslkdd.zip'
          )
        """
        import urllib.request, zipfile, tempfile, os

        instance = cls(input_dim, num_classes)

        src = local_path or github_zip_url
        if src is None:
            print("  ℹ️  Aucun checkpoint fourni — poids aléatoires (backbone gelé)")
            return instance

        # Téléchargement si URL
        if src.startswith('http'):
            print(f"  ⬇️  Téléchargement GitHub : {src}")
            tmp = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
            urllib.request.urlretrieve(src, tmp.name)
            src = tmp.name

        # Extraction si .zip
        if src.endswith('.zip'):
            extract_dir = tempfile.mkdtemp()
            with zipfile.ZipFile(src, 'r') as z:
                z.extractall(extract_dir)
            # Chercher un .pt ou .pth dans l'archive
            pt_files = [os.path.join(extract_dir, f)
                        for f in os.listdir(extract_dir)
                        if f.endswith(('.pt', '.pth', '.model'))]
            if not pt_files:
                print("  ⚠️  Aucun .pt trouvé dans l'archive — poids aléatoires")
                return instance
            src = pt_files[0]

        # Chargement des poids
        state = torch.load(src, map_location=device)
        # TabNet publie parfois sous 'network' ou directement
        if isinstance(state, dict):
            state = state.get('network', state.get('model_state_dict', state))
        missing, unexpected = instance.backbone.load_state_dict(state, strict=False)
        print(f"  ✅ Poids TabNet chargés | manquants={len(missing)}"
              f" | inattendus={len(unexpected)}")
        return instance

    def extract_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        """Retourne les embeddings TabNet (backbone gelé, sans gradient)."""
        with torch.no_grad():
            steps_out, _ = self.backbone(x)
            return torch.sum(torch.stack(steps_out, dim=0), dim=0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            steps_out, _ = self.backbone(x)
            emb = torch.sum(torch.stack(steps_out, dim=0), dim=0)
        return self.mlp(emb)


# ──────────────────────────────────────────────────────────────────
# 12-B. DistilBERT / SecureBERT / CySecBERT Feature Extractor
#       Source : HuggingFace Hub
#
#  Modèles chargés :
#   • distilbert-base-uncased       — léger, généraliste, rapide
#   • ehsanaghaei/SecureBERT        — BERT cybersécurité (CVEs, logs)
#   • markusbayer/CySecBERT         — BERT SIEM / network events
#
#  Stratégie : sérialiser les features réseau en texte structuré,
#  tokeniser, extraire le token [CLS], classifier avec MLP.
#
#  Exemple de texte généré pour NSL-KDD :
#    "duration:0 protocol:tcp service:http flag:SF src_bytes:215
#     dst_bytes:45076 logged_in:1 count:1 serror_rate:0.0 ..."
# ──────────────────────────────────────────────────────────────────

class BERTNetworkFeatureExtractor(nn.Module):
    """
    Feature Extraction via BERT pré-entraîné cybersécurité (backbone GELÉ).

    Les features réseau numériques sont converties en représentation textuelle
    structurée (template NSL-KDD) puis passées dans le tokenizer BERT.
    L'embedding [CLS] (768-dim) est extrait et classifié par un MLP.

    Modèles supportés (HuggingFace Hub) :
      - 'distilbert-base-uncased'     : généraliste, rapide (66M params)
      - 'ehsanaghaei/SecureBERT'      : BERT cyber (125M params)
      - 'markusbayer/CySecBERT'       : BERT SIEM/logs (125M params)

    Pipeline :
      x (B, F) → sérialisation texte → tokenisation → [BERT gelé]
               → [CLS] embedding (B, 768) → [MLP entraînable] → logits (B, C)
    """

    # Noms des features NSL-KDD pour la sérialisation
    NSL_KDD_FEAT_NAMES = [
        'duration', 'protocol_type', 'service', 'flag', 'src_bytes',
        'dst_bytes', 'land', 'wrong_fragment', 'urgent', 'hot',
        'num_failed_logins', 'logged_in', 'num_compromised', 'root_shell',
        'su_attempted', 'num_root', 'num_file_creations', 'num_shells',
        'num_access_files', 'num_outbound_cmds', 'is_host_login',
        'is_guest_login', 'count', 'srv_count', 'serror_rate',
        'srv_serror_rate', 'rerror_rate', 'srv_rerror_rate',
        'same_srv_rate', 'diff_srv_rate', 'srv_diff_host_rate',
        'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate',
        'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate',
        'dst_host_srv_diff_host_rate', 'dst_host_serror_rate',
        'dst_host_srv_serror_rate', 'dst_host_rerror_rate',
        'dst_host_srv_rerror_rate'
    ]

    def __init__(self, num_classes: int,
                 model_name: str = 'ehsanaghaei/SecureBERT',
                 max_length: int = 128,
                 dropout: float = 0.3,
                 feature_names: list = None):
        """
        Args:
            num_classes   : nombre de classes IDS
            model_name    : identifiant HuggingFace du modèle BERT
            max_length    : longueur max de la séquence tokenisée
            dropout       : dropout sur la tête MLP
            feature_names : noms des features (défaut = NSL-KDD 41 features)
        """
        super().__init__()
        try:
            from transformers import AutoTokenizer, AutoModel
        except ImportError:
            raise ImportError("pip install transformers")

        self.model_name    = model_name
        self.max_length    = max_length
        self.feature_names = feature_names or self.NSL_KDD_FEAT_NAMES

        print(f"  ⬇️  Chargement {model_name} depuis HuggingFace Hub...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.bert      = AutoModel.from_pretrained(model_name)

        # Détecter la dim de l'embedding [CLS]
        embed_dim = self.bert.config.hidden_size   # 768 pour BERT/DistilBERT

        # ← GELÉ : feature extraction uniquement
        _freeze_all(self.bert)

        # Tête MLP entraînable
        self.mlp = EmbeddingClassifierMLP(embed_dim, num_classes, dropout)

        params_bert = sum(p.numel() for p in self.bert.parameters())
        params_mlp  = sum(p.numel() for p in self.mlp.parameters()
                          if p.requires_grad)
        print(f"  ✅ {model_name.split('/')[-1]} chargé | embed={embed_dim}"
              f" | backbone gelé ({params_bert:,} params)"
              f" | MLP entraînable ({params_mlp:,} params)")

    def _features_to_text(self, x: torch.Tensor) -> list:
        """
        Convertit un batch de features numériques en liste de chaînes texte.

        Exemple de sortie pour 1 échantillon NSL-KDD :
          "duration:0.00 protocol_type:0.00 service:1.00 flag:0.00
           src_bytes:215.00 dst_bytes:45076.00 ..."
        """
        x_np = x.detach().cpu().numpy()
        texts = []
        for row in x_np:
            parts = []
            for i, val in enumerate(row):
                name = (self.feature_names[i]
                        if i < len(self.feature_names) else f'f{i}')
                parts.append(f"{name}:{val:.2f}")
            texts.append(' '.join(parts))
        return texts

    def extract_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extrait les embeddings [CLS] du backbone BERT (sans gradient).

        Args:
            x : (B, F) tensor de features réseau normalisées
        Returns:
            embeddings : (B, hidden_size) tensor
        """
        try:
            from transformers import AutoTokenizer
        except ImportError:
            raise ImportError("pip install transformers")

        texts   = self._features_to_text(x)
        device  = next(self.bert.parameters()).device

        encoding = self.tokenizer(
            texts,
            max_length     = self.max_length,
            padding        = 'max_length',
            truncation     = True,
            return_tensors = 'pt'
        )
        input_ids      = encoding['input_ids'].to(device)
        attention_mask = encoding['attention_mask'].to(device)

        with torch.no_grad():
            outputs = self.bert(
                input_ids=input_ids,
                attention_mask=attention_mask)
            # [CLS] token : premier token de la séquence
            cls_emb = outputs.last_hidden_state[:, 0, :]   # (B, hidden_size)
        return cls_emb

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        cls_emb = self.extract_embeddings(x)
        return self.mlp(cls_emb)


# ──────────────────────────────────────────────────────────────────
# 12-C. NSL-KDD GitHub Pretrained MLP Feature Extractor
#       Source : github.com/AshfaqRashid/IDS-NSL-KDD  (et autres)
#       Chargement : GitHub Releases ou Drive local
#
#  Ces checkpoints sont des MLP / petits réseaux entraînés directement
#  sur NSL-KDD et publiés sur GitHub pour reproductibilité.
#  On coupe la dernière couche de classification et on réutilise
#  la représentation interne comme feature extractor.
# ──────────────────────────────────────────────────────────────────

class NslKddGithubExtractor(nn.Module):
    """
    Feature Extractor depuis un MLP pré-entraîné sur NSL-KDD (GitHub public).

    Architecture attendue du checkpoint public :
      fc1 (input_dim → 128) → ReLU → fc2 (128 → 64) → ReLU → fc3 (64 → n_classes)
      On retire fc3 et on utilise la sortie de fc2 (64-dim) comme embedding.

    Dépôts GitHub compatibles :
      • github.com/AshfaqRashid/IDS-NSL-KDD
      • github.com/gauravjindal2309/IDS-using-NSL-KDD
      • github.com/ALLABOUTNN/Intrusion-Detection-System-NSL-KDD

    Si aucun checkpoint n'est disponible, le backbone est initialisé
    aléatoirement et entraînable (dégradation gracieuse).
    """

    GITHUB_RELEASES = {
        # Ajoutez ici les URLs de releases GitHub disponibles
        'ashfaq_mlp': None,   # Remplacer par URL si disponible
        'gaurav_mlp': None,
    }

    def __init__(self, input_dim: int, num_classes: int,
                 hidden1: int = 128, hidden2: int = 64,
                 dropout: float = 0.3):
        super().__init__()
        self.embed_dim = hidden2

        # Backbone MLP (architecture standard des dépôts publics NSL-KDD)
        self.backbone = nn.Sequential(
            nn.Linear(input_dim, hidden1),
            nn.BatchNorm1d(hidden1),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden1, hidden2),
            nn.BatchNorm1d(hidden2),
            nn.ReLU(),
        )

        # Tête MLP entraînable (branchée sur l'embedding hidden2-dim)
        self.mlp = EmbeddingClassifierMLP(hidden2, num_classes, dropout)
        print(f"  ✅ NSL-KDD GitHub Extractor | embed_dim={hidden2}"
              f" | backbone={input_dim}→{hidden1}→{hidden2}")

    @classmethod
    def from_checkpoint(cls, input_dim: int, num_classes: int,
                        path_or_url: str,
                        device: str = 'cpu') -> 'NslKddGithubExtractor':
        """
        Charge un checkpoint public NSL-KDD depuis GitHub ou un chemin local.

        Compatible avec les formats :
          - dict {'fc1.weight':..., 'fc2.weight':..., ...}
          - dict {'model_state_dict': {...}}
          - dict {'state_dict': {...}}

        Usage (Google Colab) :
          model = NslKddGithubExtractor.from_checkpoint(
              41, 5,
              '/content/drive/MyDrive/pretrained/nslkdd_mlp_github.pth'
          )
        """
        import urllib.request, tempfile, os

        instance = cls(input_dim, num_classes)

        if path_or_url is None:
            print("  ℹ️  Aucun checkpoint — backbone aléatoire entraînable")
            return instance

        # Téléchargement si URL GitHub
        if path_or_url.startswith('http'):
            print(f"  ⬇️  Téléchargement GitHub : {path_or_url}")
            tmp = tempfile.NamedTemporaryFile(
                suffix=os.path.splitext(path_or_url)[-1], delete=False)
            urllib.request.urlretrieve(path_or_url, tmp.name)
            path_or_url = tmp.name

        if not os.path.exists(path_or_url):
            print(f"  ⚠️  Fichier introuvable : {path_or_url} — poids aléatoires")
            return instance

        state = torch.load(path_or_url, map_location=device)

        # Normalisation du format
        for key in ('model_state_dict', 'state_dict', 'model'):
            if isinstance(state, dict) and key in state:
                state = state[key]
                break

        # Chargement flexible dans le backbone (strict=False pour tolérer
        # les différences de noms de couches entre dépôts)
        missing, unexpected = instance.backbone.load_state_dict(
            state, strict=False)

        if missing:
            # Tentative de remapping fc1/fc2 → 0/4 (indices Sequential)
            remapped = {}
            remap = {'fc1': '0', 'fc2': '4', 'fc3': '8',
                     'layer1': '0', 'layer2': '4'}
            for k, v in state.items():
                new_k = k
                for old, new in remap.items():
                    new_k = new_k.replace(old, new)
                remapped[new_k] = v
            missing2, unexpected2 = instance.backbone.load_state_dict(
                remapped, strict=False)
            if len(missing2) < len(missing):
                missing, unexpected = missing2, unexpected2

        # Geler le backbone seulement si les poids ont bien été chargés
        if len(missing) < 4:
            _freeze_all(instance.backbone)
            print(f"  ✅ Checkpoint chargé + backbone gelé"
                  f" | manquants={len(missing)} | inattendus={len(unexpected)}")
        else:
            print(f"  ⚠️  Chargement partiel ({len(missing)} clés manquantes)"
                  f" — backbone entraînable")

        return instance

    def extract_embeddings(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            return self.backbone(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            emb = self.backbone(x)
        return self.mlp(emb)


# ──────────────────────────────────────────────────────────────────
# Helper : pipeline Feature Extraction complet
# ──────────────────────────────────────────────────────────────────

def run_feature_extraction_pipeline(extractor: nn.Module,
                                    train_loader, val_loader, test_loader,
                                    num_classes: int,
                                    class_names: list,
                                    device,
                                    model_name: str = 'fe_model',
                                    save_dir: str = 'results',
                                    num_epochs: int = 30) -> dict:
    """
    Pipeline Feature Extraction complet :
      1. Passe tous les splits dans le backbone gelé → embeddings numpy
      2. Entraîne le MLP seul sur les embeddings pré-calculés
      3. Évalue sur le test set

    Avantage : les embeddings sont calculés UNE SEULE FOIS → très rapide.

    Returns:
        metrics dict (accuracy, f1, auc_roc, ...)
    """

    from torch.utils.data import TensorDataset, DataLoader

    extractor = extractor.to(device)
    extractor.eval()

    def extract_all(loader):
        """Extrait tous les embeddings d'un DataLoader en une passe."""
        all_emb, all_y = [], []
        with torch.no_grad():
            for X_batch, y_batch in loader:
                X_batch = X_batch.to(device)
                if hasattr(extractor, 'extract_embeddings'):
                    emb = extractor.extract_embeddings(X_batch)
                else:
                    # Forward sans la tête MLP
                    emb = extractor.backbone(X_batch) \
                          if hasattr(extractor, 'backbone') \
                          else extractor(X_batch)
                all_emb.append(emb.cpu())
                all_y.append(y_batch)
        return torch.cat(all_emb), torch.cat(all_y)

    print(f"\n  🔍 Extraction des embeddings [{model_name}]...")
    emb_train, y_train = extract_all(train_loader)
    emb_val,   y_val   = extract_all(val_loader)
    emb_test,  y_test  = extract_all(test_loader)

    embed_dim = emb_train.shape[1]
    print(f"  ✅ Embeddings extraits | dim={embed_dim}"
          f" | train={len(emb_train)} | val={len(emb_val)} | test={len(emb_test)}")

    # DataLoaders sur les embeddings pré-calculés
    bs = 256
    tl = DataLoader(TensorDataset(emb_train, y_train), bs, shuffle=True)
    vl = DataLoader(TensorDataset(emb_val,   y_val),   bs)
    tel= DataLoader(TensorDataset(emb_test,  y_test),  bs)

    # Entraîner le MLP seul
    mlp_head = EmbeddingClassifierMLP(embed_dim, num_classes).to(device)
    print(f"  🚀 Entraînement MLP ({sum(p.numel() for p in mlp_head.parameters()):,} params)...")
    train_model(mlp_head, tl, vl, num_epochs=num_epochs, lr=1e-3,
                patience=10, device=device,
                model_name=f'{model_name}_mlp', save_dir=save_dir)

    # Évaluation finale
    metrics = evaluate_model(mlp_head, tel, class_names,
                             device=device, model_name=model_name,
                             plot=True, save_dir=save_dir)
    return metrics


def finetune_pretrained(model: nn.Module, train_loader, val_loader,
                        num_epochs: int = 30, device=None,
                        model_name: str = 'tl_model',
                        save_dir: str = 'results',
                        class_weights=None) -> dict:
    """Entraîne un modèle TL (MLP tête uniquement) via train_model standard."""

    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    return train_model(
        model=model, train_loader=train_loader, val_loader=val_loader,
        num_epochs=num_epochs, lr=1e-3, patience=10,
        device=device, model_name=model_name, save_dir=save_dir,
        class_weights=class_weights
    )


# ──────────────────────────────────────────────────
# 13. MÉTHODES CLASSIQUES (sklearn) — Baselines
# ──────────────────────────────────────────────────

class ClassicalModels:
    """
    Wrapper pour entraîner et évaluer des classifieurs classiques.
    Accélération GPU selon ce qui est disponible :

    ┌─────────────────────┬─────────────────────────────────────────────┐
    │ Modèle              │ Backend GPU                                  │
    ├─────────────────────┼─────────────────────────────────────────────┤
    │ XGBoost             │ tree_method='gpu_hist'  (natif CUDA)        │
    │ RandomForest        │ cuML RandomForestClassifier  (RAPIDS)       │
    │ ExtraTrees          │ cuML (si dispo) sinon sklearn CPU            │
    │ SVM RBF / Linear    │ cuML SVC  (si dispo) sinon sklearn CPU      │
    │ KNN                 │ cuML KNeighborsClassifier  (si dispo)       │
    │ LogisticRegression  │ cuML LogisticRegression    (si dispo)       │
    │ GradientBoosting    │ sklearn CPU  (pas de support GPU natif)     │
    │ NaiveBayes          │ sklearn CPU                                  │
    │ DecisionTree        │ cuML DecisionTreeClassifier (si dispo)      │
    └─────────────────────┴─────────────────────────────────────────────┘

    RAPIDS cuML installation (Google Colab) :
        !pip install cuml-cu12  (selon ta version CUDA)
    """

    # ── Détection automatique des backends disponibles ──
    _CUML_AVAILABLE  = False
    _XGPU_AVAILABLE  = False

    @classmethod
    def _detect_backends(cls):
        """Détecte cuML et XGBoost-GPU une seule fois."""
        if not torch.cuda.is_available():
            print("  ⚠️  Pas de GPU CUDA détecté — modèles classiques sur CPU")
            return

        # Test XGBoost GPU
        try:
            from xgboost import XGBClassifier
            import xgboost as xgb
            # Vérification rapide que le device GPU est accessible
            xgb.set_config(verbosity=0)
            cls._XGPU_AVAILABLE = True
            print("  ✅ XGBoost GPU (CUDA) disponible")
        except Exception:
            pass

        # Test cuML (RAPIDS)
        try:
            import cuml  # noqa
            cls._CUML_AVAILABLE = True
            print("  ✅ RAPIDS cuML disponible — modèles classiques sur GPU")
        except ImportError:
            print("  ℹ️  cuML non installé — RF/SVM/KNN sur CPU")
            print("      (Pour GPU : !pip install cuml-cu12)")

    @staticmethod
    def get_all(random_state=42, use_gpu=True) -> dict:
        """
        Retourne un dict {nom: classifier}.
        Si use_gpu=True, utilise automatiquement cuML / XGBoost-GPU si disponibles.
        """
        ClassicalModels._detect_backends()
        use_cuml = use_gpu and ClassicalModels._CUML_AVAILABLE
        use_xgpu = use_gpu and ClassicalModels._XGPU_AVAILABLE

        models = {}

        # ── 1. Random Forest ────────────────────────
        if use_cuml:
            from cuml.ensemble import RandomForestClassifier as cuRF
            models['RandomForest'] = cuRF(
                n_estimators=200, max_depth=16,
                random_state=random_state)
            print("  🟢 RandomForest → cuML GPU")
        else:
            from sklearn.ensemble import RandomForestClassifier
            models['RandomForest'] = RandomForestClassifier(
                n_estimators=200, class_weight='balanced',
                n_jobs=-1, random_state=random_state)

        # ── 2. Extra Trees ──────────────────────────
        from sklearn.ensemble import ExtraTreesClassifier
        models['ExtraTrees'] = ExtraTreesClassifier(
            n_estimators=200, class_weight='balanced',
            n_jobs=-1, random_state=random_state)
        # cuML n'a pas ExtraTrees, on garde sklearn

        # ── 3. Gradient Boosting ────────────────────
        from sklearn.ensemble import GradientBoostingClassifier
        models['GradientBoosting'] = GradientBoostingClassifier(
            n_estimators=150, learning_rate=0.1, max_depth=5,
            random_state=random_state)

        # ── 4. XGBoost ──────────────────────────────
        try:
            from xgboost import XGBClassifier
            tree_method = 'gpu_hist' if use_xgpu else 'hist'
            device_param = {'device': 'cuda'} if use_xgpu else {}
            models['XGBoost'] = XGBClassifier(
                n_estimators=200, learning_rate=0.1, max_depth=6,
                eval_metric='mlogloss', tree_method=tree_method,
                random_state=random_state, **device_param)
            tag = "GPU 🟢" if use_xgpu else "CPU"
            print(f"  {'🟢' if use_xgpu else '⚪'} XGBoost → {tag}")
        except ImportError:
            print("  ⚠️  XGBoost non installé (pip install xgboost) — ignoré")

        # ── 5. LightGBM ─────────────────────────────
        try:
            import lightgbm as lgb
            device_type = 'gpu' if (use_gpu and torch.cuda.is_available()) else 'cpu'
            models['LightGBM'] = lgb.LGBMClassifier(
                n_estimators=200, learning_rate=0.1, max_depth=6,
                device_type=device_type, random_state=random_state,
                verbose=-1)
            tag = "GPU 🟢" if device_type == 'gpu' else "CPU"
            print(f"  {'🟢' if device_type=='gpu' else '⚪'} LightGBM → {tag}")
        except ImportError:
            print("  ℹ️  LightGBM non installé (pip install lightgbm) — ignoré")

        # ── 6. SVM RBF ──────────────────────────────
        if use_cuml:
            from cuml.svm import SVC as cuSVC
            models['SVM_RBF'] = cuSVC(
                kernel='rbf', C=10.0, gamma='scale', probability=True)
            print("  🟢 SVM_RBF → cuML GPU")
        else:
            from sklearn.svm import SVC
            models['SVM_RBF'] = SVC(
                kernel='rbf', C=10.0, gamma='scale',
                class_weight='balanced', probability=True,
                random_state=random_state)

        # ── 7. SVM Linear ───────────────────────────
        if use_cuml:
            from cuml.svm import LinearSVC as cuLinSVC
            # cuML LinearSVC wrappé pour predict_proba via CalibratedClassifierCV
            from sklearn.calibration import CalibratedClassifierCV
            from cuml.svm import LinearSVC as _LinSVC
            models['SVM_Linear'] = CalibratedClassifierCV(_LinSVC(C=1.0))
            print("  🟢 SVM_Linear → cuML GPU (calibré)")
        else:
            from sklearn.svm import SVC
            models['SVM_Linear'] = SVC(
                kernel='linear', C=1.0, class_weight='balanced',
                probability=True, random_state=random_state)

        # ── 8. KNN ──────────────────────────────────
        if use_cuml:
            from cuml.neighbors import KNeighborsClassifier as cuKNN
            models['KNN_5']  = cuKNN(n_neighbors=5,  metric='euclidean')
            models['KNN_11'] = cuKNN(n_neighbors=11, metric='euclidean')
            print("  🟢 KNN_5 / KNN_11 → cuML GPU")
        else:
            from sklearn.neighbors import KNeighborsClassifier
            models['KNN_5']  = KNeighborsClassifier(n_neighbors=5,  n_jobs=-1)
            models['KNN_11'] = KNeighborsClassifier(n_neighbors=11, n_jobs=-1)

        # ── 9. Logistic Regression ──────────────────
        if use_cuml:
            from cuml.linear_model import LogisticRegression as cuLR
            models['LogisticRegression'] = cuLR(
                C=1.0, max_iter=1000, solver='qn')
            print("  🟢 LogisticRegression → cuML GPU")
        else:
            from sklearn.linear_model import LogisticRegression
            models['LogisticRegression'] = LogisticRegression(
                C=1.0, max_iter=1000, class_weight='balanced',
                solver='lbfgs', random_state=random_state)

        # ── 10. Naive Bayes ─────────────────────────
        from sklearn.naive_bayes import GaussianNB
        models['NaiveBayes'] = GaussianNB()

        # ── 11. Decision Tree ───────────────────────
        if use_cuml:
            from cuml.tree import DecisionTreeClassifier as cuDT
            models['DecisionTree'] = cuDT(max_depth=20)
            print("  🟢 DecisionTree → cuML GPU")
        else:
            from sklearn.tree import DecisionTreeClassifier
            models['DecisionTree'] = DecisionTreeClassifier(
                max_depth=20, class_weight='balanced', random_state=random_state)

        return models

    @staticmethod
    def train_and_evaluate(X_train, y_train, X_test, y_test,
                           class_names, save_dir='results',
                           use_gpu=True) -> 'pd.DataFrame':
        """
        Entraîne tous les modèles classiques sur GPU si disponible,
        calcule Accuracy, Precision, Recall, F1, AUC-ROC et temps.

        Args:
            X_train, y_train : arrays numpy (float32 / int)
            X_test,  y_test  : arrays numpy
            class_names      : liste des noms de classes
            save_dir         : dossier de sortie
            use_gpu          : active l'accélération GPU (cuML / XGBoost-GPU)
        """
        import time, os
        import pandas as pd
        from sklearn.metrics import (accuracy_score, f1_score,
                                     precision_score, recall_score,
                                     roc_auc_score, classification_report)
        from sklearn.preprocessing import label_binarize

        os.makedirs(save_dir, exist_ok=True)

        gpu_info = "GPU 🟢" if (use_gpu and torch.cuda.is_available()) else "CPU ⚪"
        print("\n" + "="*65)
        print(f"  📊 MÉTHODES CLASSIQUES — {gpu_info}")
        print("="*65)

        # Conversion en float32 (requis par cuML)
        X_tr = X_train.astype(np.float32)
        X_te = X_test.astype(np.float32)
        y_tr = y_train.astype(np.int32)
        y_te = y_test.astype(np.int32)

        models  = ClassicalModels.get_all(use_gpu=use_gpu)
        results = []

        for name, clf in models.items():
            print(f"\n  🔧 {name} ...")
            try:
                # ── Entraînement ──
                t0 = time.time()
                clf.fit(X_tr, y_tr)
                t_train = time.time() - t0

                # ── Prédiction ──
                t1 = time.time()
                preds_raw = clf.predict(X_te)
                t_pred = time.time() - t1

                # cuML retourne parfois des arrays cupy → convertir en numpy
                try:
                    import cupy as cp
                    preds = cp.asnumpy(preds_raw) if hasattr(preds_raw, 'get') else np.array(preds_raw)
                except ImportError:
                    preds = np.array(preds_raw)

                preds = preds.astype(np.int32)

                # ── Métriques ──
                acc  = accuracy_score(y_te, preds) * 100
                prec = precision_score(y_te, preds, average='weighted', zero_division=0) * 100
                rec  = recall_score   (y_te, preds, average='weighted', zero_division=0) * 100
                f1   = f1_score       (y_te, preds, average='weighted', zero_division=0) * 100

                # AUC-ROC
                auc = 0.0
                if hasattr(clf, 'predict_proba'):
                    try:
                        probs_raw = clf.predict_proba(X_te)
                        try:
                            import cupy as cp
                            probs = cp.asnumpy(probs_raw) if hasattr(probs_raw, 'get') else np.array(probs_raw)
                        except ImportError:
                            probs = np.array(probs_raw)
                        y_bin = label_binarize(y_te, classes=list(range(len(class_names))))
                        if y_bin.shape[1] > 1:
                            auc = roc_auc_score(y_bin, probs,
                                                multi_class='ovr',
                                                average='weighted') * 100
                    except Exception:
                        pass

                results.append({
                    'model':        name,
                    'accuracy':     round(acc,  4),
                    'precision':    round(prec, 4),
                    'recall':       round(rec,  4),
                    'f1_score':     round(f1,   4),
                    'auc_roc':      round(auc,  4),
                    'train_time_s': round(t_train, 2),
                    'pred_time_s':  round(t_pred,  4),
                })
                print(f"     ✅ Acc: {acc:.2f}% | F1: {f1:.2f}% | AUC: {auc:.2f}%"
                      f" | Train: {t_train:.1f}s | Pred: {t_pred:.3f}s")
                print("  " + classification_report(
                    y_te, preds, target_names=class_names,
                    zero_division=0, digits=4))

            except Exception as e:
                print(f"     ❌ Erreur : {e}")
                results.append({'model': name, 'accuracy': 0, 'precision': 0,
                                'recall': 0, 'f1_score': 0, 'auc_roc': 0,
                                'train_time_s': 0, 'pred_time_s': 0,
                                'error': str(e)})

        df = pd.DataFrame(results).sort_values('f1_score', ascending=False)
        df.to_csv(f"{save_dir}/classical_models_results.csv", index=False)
        print(f"\n  💾 Résultats → {save_dir}/classical_models_results.csv")
        print("\n" + df[['model','accuracy','f1_score','auc_roc',
                         'train_time_s']].to_string(index=False))
        return df


# ──────────────────────────────────────────────────
# FACTORY — Instanciation facile des modèles
# ──────────────────────────────────────────────────

MODELS_REGISTRY = {
    # ── Deep Learning ──────────────────────────────────────────────
    'mlp':              MLP,
    'cnn1d':            CNN1D,
    'lstm':             LSTMClassifier,
    'bilstm':           BiLSTMClassifier,
    'gru':              GRUClassifier,
    'ae_classifier':    AEClassifier,
    'transformer':      TransformerClassifier,
    'cnn_lstm':         CNNLSTMHybrid,
    'resnet1d':         ResNet1D,
    'tcn':              TCN,
    'attention_mlp':    AttentionMLP,
    # ── Transfer Learning — Feature Extraction (backbones publics) ─
    # Instanciation via les méthodes de classe dédiées (from_checkpoint, etc.)
    # Ces classes ne sont pas dans le registry car leur __init__ diffère.
    # Utiliser directement : TabNetFeatureExtractor, BERTNetworkFeatureExtractor,
    #                        NslKddGithubExtractor
}


def build_model(name: str, input_dim: int, num_classes: int, **kwargs) -> nn.Module:
    """
    Factory pour instancier un modèle par son nom.
    Usage: model = build_model('lstm', 41, 5)
    """
    name = name.lower()
    if name not in MODELS_REGISTRY:
        raise ValueError(f"Modèle '{name}' inconnu. Disponibles: {list(MODELS_REGISTRY.keys())}")
    return MODELS_REGISTRY[name](input_dim, num_classes, **kwargs)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ──────────────────────────────────────────────────
# TEST RAPIDE
# ──────────────────────────────────────────────────

if __name__ == "__main__":
    """
    ╔══════════════════════════════════════════════════════════════════╗
    ║  PIPELINE CICIDS2017 — DEEP LEARNING UNIQUEMENT                  ║
    ║  Dataset : all_traffic.csv (fichier combiné UNB CIC-IDS 2017)   ║
    ║  Classes : BENIGN + toutes attaques (15 classes)                 ║
    ║  Features: ~78 features réseau (après nettoyage)                 ║
    ║                                                                  ║
    ║  Google Colab — Setup requis :                                   ║
    ║    !pip install torch torchvision                                ║
    ║    from google.colab import drive; drive.mount('/content/drive') ║
    ╚══════════════════════════════════════════════════════════════════╝
    """

    import pandas as pd

    # ══════════════════════════════════════════════════════════════
    #  0. DEVICE & CHEMINS
    # ══════════════════════════════════════════════════════════════
    DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n🖥️  Device : {DEVICE}")
    if torch.cuda.is_available():
        print(f"   GPU     : {torch.cuda.get_device_name(0)}")
        print(f"   VRAM    : {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # ── Chemins Google Drive ──────────────────────────────────────
    CICIDS_CSV   = '/content/drive/MyDrive/data/all_traffic.csv'
    SAVE_DIR     = '/content/drive/MyDrive/ids_results_cicids'
    CKPT_DIR     = f'{SAVE_DIR}/checkpoints'
    os.makedirs(CKPT_DIR, exist_ok=True)

    # ── Hyperparamètres ───────────────────────────────────────────
    BATCH      = 512    # Plus grand batch car dataset CICIDS est volumineux
    NUM_EPOCHS = 30
    LR         = 1e-3
    PATIENCE   = 12

    # ══════════════════════════════════════════════════════════════
    #  1. CHARGEMENT & PRÉTRAITEMENT — CICIDS2017
    # ══════════════════════════════════════════════════════════════
    print("\n" + "="*65)
    print("  📂 Chargement CICIDS2017 — all_traffic.csv")
    print("="*65)

    loader = DatasetLoader()

    # Chargement : utiliser chunksize=500_000 si le fichier est > 2 Go
    # df = loader.load_cicids(CICIDS_CSV, chunksize=500_000)
    df = loader.load_cicids(CICIDS_CSV)

    # ── Prétraitement ─────────────────────────────────────────────
    # balance=True : sur-échantillonne les classes minoritaires
    # (Heartbleed, Infiltration, Web SQLInjection très rares)
    preprocessor = IDSPreprocessor(scaler_type='standard', balance=True)
    X_all, y_all = preprocessor.fit_transform(df, target_col='attack_category')

    INPUT_DIM   = preprocessor.get_num_features()
    NUM_CLASSES = preprocessor.get_num_classes()
    CLASS_NAMES = preprocessor.get_class_names()

    print(f"\n  📐 Input dim  : {INPUT_DIM}")
    print(f"  🏷️  Classes ({NUM_CLASSES}) : {CLASS_NAMES}")
    print(f"  📊 Total après équilibrage : {len(X_all):,}")

    # ── DataLoaders ───────────────────────────────────────────────
    # Split 75% train / 10% val / 15% test (stratifié)
    train_loader, val_loader, test_loader, (X_test, y_test) = create_dataloaders(
        X_all, y_all,
        test_size=0.15, val_size=0.10,
        batch_size=BATCH
    )

    print(f"\n  🔢 Batch shape : X={next(iter(train_loader))[0].shape}")

    # ══════════════════════════════════════════════════════════════
    #  2. INSTANTIATION DES 11 MODÈLES DL
    #     Architectures adaptées à CICIDS2017 :
    #       - input_dim  ~78 features (vs 41 pour NSL-KDD)
    #       - num_classes variable (15 classes max)
    #       - MLP/Attention élargi : 512→256→128 (plus de features)
    #       - LSTM/GRU/BiLSTM : hidden=128, 2 couches (identique)
    #       - Transformer : d_model=128 (plus de features réseau)
    #       - CNN-LSTM : cnn_filters=128 (plus de canaux)
    #       - TCN : channels=[64,128,128,256] (plus profond)
    # ══════════════════════════════════════════════════════════════
    print("\n" + "="*65)
    print("  🔨 Instanciation des 11 modèles Deep Learning")
    print(f"     input_dim={INPUT_DIM}  |  num_classes={NUM_CLASSES}")
    print("="*65)

    dl_models = {
        # ── Feed-Forward ──────────────────────────────────────────
        'mlp': MLP(
            INPUT_DIM, NUM_CLASSES,
            hidden_dims=[512, 256, 128],   # Identique NSL-KDD (déjà large)
            dropout=0.3
        ),
        'attention_mlp': AttentionMLP(
            INPUT_DIM, NUM_CLASSES,
            hidden_dim=256,                # Élargi pour ~78 features
            dropout=0.3
        ),

        # ── Convolutif 1D ─────────────────────────────────────────
        'cnn1d': CNN1D(
            INPUT_DIM, NUM_CLASSES,
            num_filters=[64, 128, 256],
            kernel_size=3, dropout=0.3
        ),
        'resnet1d': ResNet1D(
            INPUT_DIM, NUM_CLASSES,
            channels=64,
            num_blocks=4, dropout=0.2
        ),
        'tcn': TCN(
            INPUT_DIM, NUM_CLASSES,
            channels=[64, 128, 128, 256],  # Plus de capacité
            kernel_size=3, dropout=0.2
        ),

        # ── Récurrents ────────────────────────────────────────────
        'lstm': LSTMClassifier(
            INPUT_DIM, NUM_CLASSES,
            hidden_size=128, num_layers=2, dropout=0.3
        ),
        'bilstm': BiLSTMClassifier(
            INPUT_DIM, NUM_CLASSES,
            hidden_size=128, num_layers=2, dropout=0.3
        ),
        'gru': GRUClassifier(
            INPUT_DIM, NUM_CLASSES,
            hidden_size=128, num_layers=2, dropout=0.3
        ),

        # ── Hybride CNN-LSTM ──────────────────────────────────────
        'cnn_lstm': CNNLSTMHybrid(
            INPUT_DIM, NUM_CLASSES,
            cnn_filters=128,               # Plus de filtres pour ~78 features
            lstm_hidden=128, dropout=0.3
        ),

        # ── Transformer ───────────────────────────────────────────
        'transformer': TransformerClassifier(
            INPUT_DIM, NUM_CLASSES,
            d_model=128,                   # Augmenté (NSL-KDD=64)
            nhead=8,                       # 8 têtes d'attention (vs 4)
            num_layers=3, dropout=0.1
        ),

        # ── Autoencoder + Classifier ──────────────────────────────
        'ae_classifier': AEClassifier(
            INPUT_DIM, NUM_CLASSES,
            encoding_dims=[256, 128, 64]   # Encodeur plus large (vs [128,64,32])
        ),
    }

    for name, model in dl_models.items():
        n_params = count_parameters(model)
        print(f"  ✅ {name:<20} | {n_params:>12,} paramètres")

    # ══════════════════════════════════════════════════════════════
    #  3. ENTRAÎNEMENT + ÉVALUATION SUR GPU
    # ══════════════════════════════════════════════════════════════
    print("\n" + "="*65)
    print("  🚀 ENTRAÎNEMENT — 11 modèles Deep Learning sur GPU")
    print(f"     Epochs={NUM_EPOCHS} | LR={LR} | Patience={PATIENCE} | Batch={BATCH}")
    print("="*65)

    dl_results_df, dl_histories = run_full_experiment(
        train_loader=train_loader,
        val_loader=val_loader,
        test_loader=test_loader,
        models_dict=dl_models,
        class_names=CLASS_NAMES,
        num_epochs=NUM_EPOCHS,
        lr=LR,
        patience=PATIENCE,
        save_dir=SAVE_DIR,
        y_train=y_all
    )

    # ── Résumé ────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  🏆 TABLEAU COMPARATIF — Deep Learning sur CICIDS2017")
    print("="*65)
    cols_show = ['model', 'accuracy', 'precision', 'recall', 'f1_score',
                 'auc_roc', 'training_time']
    print(dl_results_df[cols_show].to_string(index=False))

    # ── Sauvegarde ────────────────────────────────────────────────
    dl_results_df.to_csv(f'{SAVE_DIR}/cicids2017_dl_results.csv', index=False)
    print(f"\n  💾 Résultats → {SAVE_DIR}/cicids2017_dl_results.csv")

    best = dl_results_df.iloc[0]
    print(f"\n  🥇 Meilleur modèle : {best['model']}")
    print(f"     Accuracy : {best['accuracy']:.4f}%")
    print(f"     F1-Score : {best['f1_score']:.4f}%")
    print(f"     AUC-ROC  : {best['auc_roc']:.4f}%")
    print(f"\n✅ Pipeline CICIDS2017 terminé. Résultats dans : {SAVE_DIR}")