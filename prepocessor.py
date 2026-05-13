"""
========================================================
  IDS Project - Étape 1 : Collecte & Préparation des Données
  Auteur : Projet de Fin d'Études - Ingénieur IA
  Datasets supportés : NSL-KDD, CICIDS2017, UNSW-NB15, KDD99
========================================================
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from sklearn.utils import resample
import torch
from torch.utils.data import Dataset, DataLoader
import os
import warnings
warnings.filterwarnings('ignore')


# ──────────────────────────────────────────────────
# 1. CHARGEMENT DES DATASETS
# ──────────────────────────────────────────────────

class DatasetLoader:
    """
    Charge et formate différents datasets IDS.
    Datasets supportés : NSL-KDD, CICIDS2017, UNSW-NB15, KDD99
    """

    # Colonnes NSL-KDD
    NSL_KDD_COLUMNS = [
        'duration','protocol_type','service','flag','src_bytes','dst_bytes',
        'land','wrong_fragment','urgent','hot','num_failed_logins','logged_in',
        'num_compromised','root_shell','su_attempted','num_root','num_file_creations',
        'num_shells','num_access_files','num_outbound_cmds','is_host_login',
        'is_guest_login','count','srv_count','serror_rate','srv_serror_rate',
        'rerror_rate','srv_rerror_rate','same_srv_rate','diff_srv_rate',
        'srv_diff_host_rate','dst_host_count','dst_host_srv_count',
        'dst_host_same_srv_rate','dst_host_diff_srv_rate','dst_host_same_src_port_rate',
        'dst_host_srv_diff_host_rate','dst_host_serror_rate','dst_host_srv_serror_rate',
        'dst_host_rerror_rate','dst_host_srv_rerror_rate','label','difficulty'
    ]

    # Mapping des attaques NSL-KDD en catégories
    NSL_KDD_ATTACK_MAP = {
        'normal': 'Normal',
        'back': 'DoS', 'land': 'DoS', 'neptune': 'DoS', 'pod': 'DoS',
        'smurf': 'DoS', 'teardrop': 'DoS', 'mailbomb': 'DoS',
        'apache2': 'DoS', 'processtable': 'DoS', 'udpstorm': 'DoS',
        'ipsweep': 'Probe', 'nmap': 'Probe', 'portsweep': 'Probe',
        'satan': 'Probe', 'mscan': 'Probe', 'saint': 'Probe',
        'ftp_write': 'R2L', 'guess_passwd': 'R2L', 'imap': 'R2L',
        'multihop': 'R2L', 'phf': 'R2L', 'spy': 'R2L', 'warezclient': 'R2L',
        'warezmaster': 'R2L', 'sendmail': 'R2L', 'named': 'R2L',
        'snmpgetattack': 'R2L', 'snmpguess': 'R2L', 'xlock': 'R2L',
        'xsnoop': 'R2L', 'worm': 'R2L',
        'buffer_overflow': 'U2R', 'loadmodule': 'U2R', 'perl': 'U2R',
        'rootkit': 'U2R', 'httptunnel': 'U2R', 'ps': 'U2R',
        'sqlattack': 'U2R', 'xterm': 'U2R'
    }

    @staticmethod
    def load_nsl_kdd(train_path: str, test_path: str = None):
        """Charge le dataset NSL-KDD (.txt ou .csv)"""
        print("📂 Chargement NSL-KDD...")
        df_train = pd.read_csv(train_path, header=None,
                               names=DatasetLoader.NSL_KDD_COLUMNS)
        df_train.drop('difficulty', axis=1, inplace=True, errors='ignore')

        df_test = None
        if test_path:
            df_test = pd.read_csv(test_path, header=None,
                                  names=DatasetLoader.NSL_KDD_COLUMNS)
            df_test.drop('difficulty', axis=1, inplace=True, errors='ignore')

        # Mapper les attaques en catégories
        def map_label(label):
            label = label.strip().rstrip('.')
            return DatasetLoader.NSL_KDD_ATTACK_MAP.get(label, 'Unknown')

        df_train['attack_category'] = df_train['label'].apply(map_label)
        if df_test is not None:
            df_test['attack_category'] = df_test['label'].apply(map_label)

        print(f"  ✅ Train: {len(df_train)} lignes | Classes: {df_train['attack_category'].value_counts().to_dict()}")
        return df_train, df_test

    # ── Colonnes à supprimer (IPs, ports sources, timestamps, doublons) ──
    CICIDS_DROP_COLS = [
        'Flow ID', 'Source IP', 'Source Port', 'Destination IP',
        'Destination Port', 'Timestamp', 'SimillarHTTP',
        ' Flow ID', ' Source IP', ' Source Port', ' Destination IP',
        ' Destination Port', ' Timestamp',
    ]

    # ── Mapping exhaustif des labels CICIDS2017 → catégories normalisées ──
    CICIDS_LABEL_MAP = {
        # Trafic normal
        'BENIGN':                               'BENIGN',
        # DoS / DDoS
        'DoS Hulk':                             'DoS_Hulk',
        'DoS GoldenEye':                        'DoS_GoldenEye',
        'DoS slowloris':                        'DoS_Slowloris',
        'DoS Slowhttptest':                     'DoS_SlowHTTPTest',
        'Heartbleed':                           'Heartbleed',
        'DDoS':                                 'DDoS',
        # Scans / reconnaissance
        'PortScan':                             'PortScan',
        'FTP-Patator':                          'FTP_Patator',
        'SSH-Patator':                          'SSH_Patator',
        # Web
        'Web Attack \x96 Brute Force':          'Web_BruteForce',
        'Web Attack – Brute Force':             'Web_BruteForce',
        'Web Attack ï¿½ Brute Force':           'Web_BruteForce',
        'Web Attack \x96 XSS':                  'Web_XSS',
        'Web Attack – XSS':                     'Web_XSS',
        'Web Attack ï¿½ XSS':                   'Web_XSS',
        'Web Attack \x96 Sql Injection':        'Web_SQLInjection',
        'Web Attack – Sql Injection':           'Web_SQLInjection',
        'Web Attack ï¿½ Sql Injection':         'Web_SQLInjection',
        # Infiltration / Botnet
        'Infiltration':                         'Infiltration',
        'Bot':                                  'Bot',
    }

    @staticmethod
    def load_cicids(path: str, chunksize: int = None):
        """
        Charge CICIDS2017 (all_traffic.csv ou fichiers journaliers).

        Gestion spécifique CICIDS2017 :
          - Nettoyage des noms de colonnes (espaces, BOM)
          - Suppression colonnes non-numériques (IP, Port, Timestamp)
          - Remplacement Inf / -Inf → NaN puis médiane
          - Mapping exhaustif des labels → classes normalisées
          - Support chargement par chunks pour fichiers >1 Go

        Args:
            path      : chemin vers all_traffic.csv
            chunksize : si fourni, charge par morceaux (utile > 1 Go)
        """
        print("📂 Chargement CICIDS2017...")

        if chunksize:
            chunks = []
            for i, chunk in enumerate(pd.read_csv(path, low_memory=False,
                                                   chunksize=chunksize)):
                chunk.columns = chunk.columns.str.strip().str.replace('\ufeff', '')
                chunks.append(chunk)
                print(f"  Chunk {i+1} : {len(chunk):,} lignes")
            df = pd.concat(chunks, ignore_index=True)
        else:
            df = pd.read_csv(path, low_memory=False)
            df.columns = df.columns.str.strip().str.replace('\ufeff', '')

        # ── 1. Identifier et renommer la colonne label ──────────────
        label_col = next((c for c in df.columns if c.strip().lower() == 'label'), None)
        if label_col is None:
            label_col = next((c for c in df.columns if 'label' in c.lower()), None)
        if label_col is None:
            raise ValueError(f"Colonne 'Label' introuvable. Colonnes: {df.columns.tolist()}")
        df.rename(columns={label_col: 'label'}, inplace=True)

        # ── 2. Supprimer colonnes non-informatives ──────────────────
        cols_to_drop = [c for c in DatasetLoader.CICIDS_DROP_COLS if c in df.columns]
        df.drop(columns=cols_to_drop, inplace=True, errors='ignore')

        # ── 3. Remplacer Inf / -Inf → NaN ──────────────────────────
        num_cols = df.select_dtypes(include=[np.number]).columns
        n_inf = np.isinf(df[num_cols]).sum().sum()
        if n_inf > 0:
            df[num_cols] = df[num_cols].replace([np.inf, -np.inf], np.nan)
            print(f"  ⚠️  {n_inf:,} valeurs Inf remplacées par NaN")

        # ── 4. Mapper les labels → catégories normalisées ───────────
        def _map_label(raw: str) -> str:
            raw = str(raw).strip()
            if raw.upper() == 'BENIGN':
                return 'BENIGN'
            # Recherche directe
            if raw in DatasetLoader.CICIDS_LABEL_MAP:
                return DatasetLoader.CICIDS_LABEL_MAP[raw]
            # Recherche insensible à la casse
            raw_lower = raw.lower()
            for k, v in DatasetLoader.CICIDS_LABEL_MAP.items():
                if k.lower() == raw_lower:
                    return v
            # Fallback : normaliser le nom brut
            return raw.replace(' ', '_').replace('-', '_')

        df['attack_category'] = df['label'].apply(_map_label)

        # ── 5. Stats ────────────────────────────────────────────────
        class_dist = df['attack_category'].value_counts().to_dict()
        n_classes   = df['attack_category'].nunique()
        n_features  = len(df.columns) - 2   # -label -attack_category
        print(f"  ✅ {len(df):,} lignes | {n_features} features | {n_classes} classes")
        print(f"  📊 Distribution :")
        for cls, cnt in sorted(class_dist.items(), key=lambda x: -x[1]):
            pct = cnt / len(df) * 100
            print(f"       {cls:<30} {cnt:>8,}  ({pct:5.2f}%)")

        return df

    @staticmethod
    def load_unsw_nb15(train_path: str, test_path: str = None):
        """Charge UNSW-NB15"""
        print("📂 Chargement UNSW-NB15...")
        df_train = pd.read_csv(train_path)
        df_train.columns = df_train.columns.str.strip().str.lower()
        # Label binary + categorie
        if 'attack_cat' in df_train.columns:
            df_train['attack_category'] = df_train['attack_cat'].fillna('Normal').str.strip()
        else:
            df_train['attack_category'] = df_train['label'].map({0: 'Normal', 1: 'Attack'})

        df_test = None
        if test_path:
            df_test = pd.read_csv(test_path)
            df_test.columns = df_test.columns.str.strip().str.lower()
            if 'attack_cat' in df_test.columns:
                df_test['attack_category'] = df_test['attack_cat'].fillna('Normal').str.strip()

        print(f"  ✅ Train: {len(df_train)} lignes")
        return df_train, df_test


# ──────────────────────────────────────────────────
# 2. PREPROCESSING
# ──────────────────────────────────────────────────

class IDSPreprocessor:
    """
    Pipeline complet de prétraitement pour IDS.
    - Gestion valeurs manquantes & aberrantes
    - Encodage des variables catégorielles
    - Normalisation / Standardisation
    - Équilibrage des classes (SMOTE-like)
    """

    def __init__(self, scaler_type='standard', balance=True):
        self.scaler_type = scaler_type
        self.balance = balance
        self.scaler = StandardScaler() if scaler_type == 'standard' else MinMaxScaler()
        self.label_encoders = {}
        self.target_encoder = LabelEncoder()
        self.feature_columns = None
        self.categorical_columns = None

    def _handle_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Gestion des valeurs manquantes"""
        # Colonnes numériques : médiane
        num_cols = df.select_dtypes(include=[np.number]).columns
        df[num_cols] = df[num_cols].fillna(df[num_cols].median())
        # Colonnes catégorielles : mode
        cat_cols = df.select_dtypes(include=['object']).columns
        for col in cat_cols:
            df[col] = df[col].fillna(df[col].mode()[0] if len(df[col].mode()) > 0 else 'unknown')
        return df

    def _handle_outliers(self, df: pd.DataFrame, threshold=3.0) -> pd.DataFrame:
        """Suppression des outliers par Z-score"""
        num_cols = df.select_dtypes(include=[np.number]).columns
        for col in num_cols:
            mean, std = df[col].mean(), df[col].std()
            if std > 0:
                df[col] = df[col].clip(mean - threshold * std, mean + threshold * std)
        return df

    def _encode_categoricals(self, df: pd.DataFrame, fit=True) -> pd.DataFrame:
        """Encodage Label des variables catégorielles"""
        cat_cols = df.select_dtypes(include=['object']).columns.tolist()
        # Exclure la colonne cible
        cat_cols = [c for c in cat_cols if c not in ['label', 'attack_category']]

        for col in cat_cols:
            if fit:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                if col in self.label_encoders:
                    le = self.label_encoders[col]
                    # Gérer les classes inconnues
                    known = set(le.classes_)
                    df[col] = df[col].astype(str).apply(
                        lambda x: x if x in known else le.classes_[0])
                    df[col] = le.transform(df[col])
        return df

    def _balance_classes(self, X: np.ndarray, y: np.ndarray,
                         max_cap: int = 50_000,
                         target_ratio: float = 0.10) -> tuple:
        """
        Sur-échantillonnage adaptatif des classes minoritaires.

        Stratégie :
          - Classe dominante (BENIGN) : plafonnée à max_cap pour éviter
            un déséquilibre écrasant (CICIDS2017 a ~80% BENIGN).
          - Classes minoritaires : sur-échantillonnées jusqu'à
            max(leur taille actuelle, max_cap * target_ratio).
          - Aucune classe n'est sous-échantillonnée en dessous de son
            effectif réel (on n'enlève pas de données).

        Args:
            max_cap      : plafond pour la classe majoritaire (défaut 50 000)
            target_ratio : fraction de max_cap visée pour les petites classes
        """
        df_temp = pd.DataFrame(X)
        df_temp['__label__'] = y

        counts    = df_temp['__label__'].value_counts()
        dominant  = counts.index[0]
        target_n  = max(int(max_cap * target_ratio),
                        int(counts.median()))

        balanced = []
        for label in counts.index:
            subset = df_temp[df_temp['__label__'] == label]
            n_cur  = len(subset)

            if label == dominant:
                # Sous-échantillonnage de la classe dominante
                n_new = min(n_cur, max_cap)
                subset = subset.sample(n=n_new, random_state=42)
            elif n_cur < target_n:
                # Sur-échantillonnage des classes minoritaires
                subset = resample(subset, replace=True,
                                  n_samples=target_n, random_state=42)
            balanced.append(subset)

        df_balanced = pd.concat(balanced).sample(frac=1, random_state=42)
        X_bal = df_balanced.drop('__label__', axis=1).values
        y_bal = df_balanced['__label__'].values

        before = {int(k): int(v) for k, v in counts.to_dict().items()}
        after  = {int(k): int(v)
                  for k, v in pd.Series(y_bal).value_counts().sort_index().to_dict().items()}
        print(f"  ⚖️  Équilibrage classes (avant → après) :")
        for lbl in sorted(before.keys()):
            b, a = before.get(lbl, 0), after.get(lbl, 0)
            print(f"       Classe {lbl:<3} : {b:>8,} → {a:>8,}")
        return X_bal, y_bal

    def fit_transform(self, df: pd.DataFrame, target_col='attack_category'):
        """Pipeline complet d'entraînement"""
        print("\n🔧 Prétraitement en cours...")
        df = df.copy()

        # 1. Valeurs manquantes
        df = self._handle_missing(df)
        print("  ✅ Valeurs manquantes traitées")

        # 2. Outliers
        df = self._handle_outliers(df)
        print("  ✅ Outliers traités")

        # 3. Encodage
        df = self._encode_categoricals(df, fit=True)
        print("  ✅ Variables catégorielles encodées")

        # 4. Séparation features / target
        cols_to_drop = [c for c in ['label', 'attack_category'] if c in df.columns]
        self.feature_columns = [c for c in df.columns if c not in cols_to_drop]

        X = df[self.feature_columns].values.astype(np.float32)
        y_raw = df[target_col].values
        y = self.target_encoder.fit_transform(y_raw)

        print(f"  ✅ Classes encodées: {dict(enumerate(self.target_encoder.classes_))}")

        # 5. Normalisation
        X = self.scaler.fit_transform(X).astype(np.float32)
        print("  ✅ Normalisation appliquée")

        # 6. Équilibrage
        if self.balance:
            X, y = self._balance_classes(X, y)

        return X, y

    def transform(self, df: pd.DataFrame, target_col='attack_category'):
        """Transformation (sans fit) pour test/validation"""
        df = df.copy()
        df = self._handle_missing(df)
        df = self._handle_outliers(df)
        df = self._encode_categoricals(df, fit=False)

        cols_to_drop = [c for c in ['label', 'attack_category'] if c in df.columns]
        X = df[self.feature_columns].values.astype(np.float32)
        y_raw = df[target_col].values

        # Gérer les classes inconnues dans le test
        known_classes = set(self.target_encoder.classes_)
        y_raw_safe = [c if c in known_classes else self.target_encoder.classes_[0]
                      for c in y_raw]
        y = self.target_encoder.transform(y_raw_safe)

        X = self.scaler.transform(X).astype(np.float32)
        return X, y

    def get_class_names(self):
        return list(self.target_encoder.classes_)

    def get_num_classes(self):
        return len(self.target_encoder.classes_)

    def get_num_features(self):
        return len(self.feature_columns)


# ──────────────────────────────────────────────────
# 3. PYTORCH DATASET
# ──────────────────────────────────────────────────

class IDSDataset(Dataset):
    """Dataset PyTorch pour IDS"""

    def __init__(self, X: np.ndarray, y: np.ndarray, reshape_for_cnn=False):
        self.X = torch.FloatTensor(X)
        self.y = torch.LongTensor(y)
        self.reshape_for_cnn = reshape_for_cnn  # (batch, 1, features) pour CNN 1D

    def __len__(self):
        return len(self.y)

    def __getitem__(self, idx):
        x = self.X[idx]
        if self.reshape_for_cnn:
            x = x.unsqueeze(0)  # (1, features)
        return x, self.y[idx]


def create_dataloaders(X, y, test_size=0.2, val_size=0.1, batch_size=256,
                       reshape_for_cnn=False):
    """
    Crée les DataLoaders train/val/test PyTorch.
    Returns: train_loader, val_loader, test_loader
    """
    # Split train/temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=test_size + val_size, random_state=42, stratify=y)

    # Split val/test depuis temp
    rel_val = val_size / (test_size + val_size)
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=1 - rel_val, random_state=42, stratify=y_temp)

    print(f"\n📊 Division des données:")
    print(f"  Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")

    train_ds = IDSDataset(X_train, y_train, reshape_for_cnn)
    val_ds   = IDSDataset(X_val,   y_val,   reshape_for_cnn)
    test_ds  = IDSDataset(X_test,  y_test,  reshape_for_cnn)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=2, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)

    return train_loader, val_loader, test_loader, (X_test, y_test)


# ──────────────────────────────────────────────────
# 4. EXEMPLE D'UTILISATION
# ──────────────────────────────────────────────────

if __name__ == "__main__":

    # ── CICIDS2017 — all_traffic.csv depuis Google Drive ──
    from google.colab import drive
    drive.mount('/content/drive')

    CICIDS_PATH = '/content/drive/MyDrive/data/all_traffic.csv'

    loader = DatasetLoader()

    # Chargement (utiliser chunksize=500_000 si le fichier dépasse 2 Go)
    df = loader.load_cicids(CICIDS_PATH)

    # Prétraitement complet
    preprocessor = IDSPreprocessor(scaler_type='standard', balance=True)
    X_processed, y_processed = preprocessor.fit_transform(
        df, target_col='attack_category')

    print(f"\n✅ Features : {X_processed.shape[1]}")
    print(f"✅ Samples  : {X_processed.shape[0]:,}")
    print(f"✅ Classes ({preprocessor.get_num_classes()}) : {preprocessor.get_class_names()}")

    # DataLoaders
    train_loader, val_loader, test_loader, (X_test, y_test) = create_dataloaders(
        X_processed, y_processed,
        test_size=0.15, val_size=0.10,
        batch_size=256
    )

    for X_batch, y_batch in train_loader:
        print(f"\n✅ Batch : X={X_batch.shape}, y={y_batch.shape}")
        break

    print("\n✅ Pipeline CICIDS2017 prêt !")
    print(f"   Num features : {preprocessor.get_num_features()}")
    print(f"   Num classes  : {preprocessor.get_num_classes()}")