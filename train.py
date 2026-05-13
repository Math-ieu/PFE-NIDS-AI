import torch
import torch.nn as nn
import torch.optim as optim
from torch.optim.lr_scheduler import ReduceLROnPlateau, CosineAnnealingLR
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (classification_report, confusion_matrix,
                              accuracy_score, f1_score, precision_score,
                              recall_score, roc_auc_score, roc_curve,
                              auc as auc_score)
from sklearn.preprocessing import label_binarize
import time
import os
import json
from pathlib import Path


# ──────────────────────────────────────────────────
# 1. EARLY STOPPING
# ──────────────────────────────────────────────────

class EarlyStopping:
    """Arrêt anticipé basé sur la loss de validation."""
    def __init__(self, patience=10, min_delta=1e-4, restore_best=True):
        self.patience = patience
        self.min_delta = min_delta
        self.restore_best = restore_best
        self.counter = 0
        self.best_loss = float('inf')
        self.best_state = None
        self.stopped = False

    def __call__(self, val_loss, model):
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
            if self.restore_best:
                self.best_state = {k: v.cpu().clone()
                                   for k, v in model.state_dict().items()}
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.stopped = True
                if self.restore_best and self.best_state:
                    model.load_state_dict(self.best_state)
        return self.stopped


# ──────────────────────────────────────────────────
# 2. BOUCLE D'ENTRAÎNEMENT UNIVERSEL
# ──────────────────────────────────────────────────

def train_model(model, train_loader, val_loader, num_epochs=50,
                lr=1e-3, weight_decay=1e-4, patience=10,
                scheduler_type='plateau', device=None,
                model_name='model', save_dir='checkpoints',
                class_weights=None):
    """
    Entraîne un modèle PyTorch.

    Args:
        model          : nn.Module PyTorch
        train_loader   : DataLoader d'entraînement
        val_loader     : DataLoader de validation
        num_epochs     : Nombre max d'époques
        lr             : Learning rate initial
        weight_decay   : Régularisation L2
        patience       : Patience pour EarlyStopping
        scheduler_type : 'plateau' | 'cosine'
        device         : 'cuda' | 'cpu' | None (auto)
        model_name     : Nom pour sauvegarde
        save_dir       : Répertoire de sauvegarde
        class_weights  : Tensor de poids par classe (gestion déséquilibre)

    Returns:
        history (dict): Historique train/val loss & accuracy
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    print(f"\n🚀 Entraînement de [{model_name}] sur {device}")

    # Loss avec gestion du déséquilibre de classes
    if class_weights is not None:
        class_weights = class_weights.to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    # Scheduler
    if scheduler_type == 'plateau':
        scheduler = ReduceLROnPlateau(optimizer, patience=5, factor=0.5,
                                      min_lr=1e-6)
    else:
        scheduler = CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=1e-6)

    early_stop = EarlyStopping(patience=patience)
    os.makedirs(save_dir, exist_ok=True)

    history = {'train_loss': [], 'val_loss': [],
               'train_acc': [], 'val_acc': []}
    best_val_acc = 0.0
    start_time = time.time()

    for epoch in range(num_epochs):
        # ── Phase d'entraînement ──
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0

        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()

            output = model(X_batch)
            if isinstance(output, tuple):  # Autoencoder
                logits, x_hat = output
                loss = criterion(logits, y_batch)
                # + terme de reconstruction
                loss += 0.1 * nn.MSELoss()(x_hat, X_batch)
            else:
                logits = output
                loss = criterion(logits, y_batch)

            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            train_loss += loss.item()
            preds = logits.argmax(dim=1)
            train_correct += (preds == y_batch).sum().item()
            train_total += len(y_batch)

        # ── Phase de validation ──
        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0

        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                output = model(X_batch)
                logits = output[0] if isinstance(output, tuple) else output
                loss = criterion(logits, y_batch)

                val_loss += loss.item()
                preds = logits.argmax(dim=1)
                val_correct += (preds == y_batch).sum().item()
                val_total += len(y_batch)

        # Moyennes
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss   = val_loss   / len(val_loader)
        train_acc = 100.0 * train_correct / train_total
        val_acc   = 100.0 * val_correct   / val_total

        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(avg_val_loss)
        history['train_acc'].append(train_acc)
        history['val_acc'].append(val_acc)

        # Scheduler step
        if scheduler_type == 'plateau':
            scheduler.step(avg_val_loss)
        else:
            scheduler.step()

        # Sauvegarde meilleur modèle
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(),
                       f"{save_dir}/{model_name}_best.pth")

        # Log toutes les 5 époques
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d}/{num_epochs} | "
                  f"Train Loss: {avg_train_loss:.4f} Acc: {train_acc:.2f}% | "
                  f"Val Loss: {avg_val_loss:.4f} Acc: {val_acc:.2f}%")

        # Early stopping
        if early_stop(avg_val_loss, model):
            print(f"  ⏹  Early stopping à l'époque {epoch+1}")
            break

    elapsed = time.time() - start_time
    print(f"  Terminé en {elapsed:.1f}s | Meilleure Val Acc: {best_val_acc:.2f}%")
    history['training_time'] = elapsed
    history['best_val_acc'] = best_val_acc
    return history


# ──────────────────────────────────────────────────
# 3. ÉVALUATION COMPLÈTE
# ──────────────────────────────────────────────────

def evaluate_model(model, test_loader, class_names, device=None,
                   model_name='model', plot=True, save_dir='results'):
    """
    Évalue un modèle et affiche/sauvegarde toutes les métriques.

    Returns:
        dict: Toutes les métriques de performance
    """
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.eval()
    model.to(device)
    os.makedirs(save_dir, exist_ok=True)

    all_preds, all_labels, all_probs = [], [], []

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)
            output = model(X_batch)
            logits = output[0] if isinstance(output, tuple) else output

            probs = torch.softmax(logits, dim=1).cpu().numpy()
            preds = logits.argmax(dim=1).cpu().numpy()

            all_preds.extend(preds)
            all_labels.extend(y_batch.numpy())
            all_probs.extend(probs)

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)

    # ── Métriques principales ──
    acc       = accuracy_score(all_labels, all_preds) * 100
    precision = precision_score(all_labels, all_preds, average='weighted',
                                zero_division=0) * 100
    recall    = recall_score(all_labels, all_preds, average='weighted',
                             zero_division=0) * 100
    f1        = f1_score(all_labels, all_preds, average='weighted',
                         zero_division=0) * 100

    # AUC ROC (multiclasse)
    try:
        y_bin = label_binarize(all_labels, classes=list(range(len(class_names))))
        auc = roc_auc_score(y_bin, all_probs, multi_class='ovr',
                            average='weighted') * 100
    except Exception:
        auc = 0.0

    metrics = {
        'model': model_name,
        'accuracy':  round(acc, 4),
        'precision': round(precision, 4),
        'recall':    round(recall, 4),
        'f1_score':  round(f1, 4),
        'auc_roc':   round(auc, 4),
    }

    # Rapport détaillé
    print(f"\n{'='*60}")
    print(f"  Évaluation : {model_name}")
    print(f"{'='*60}")
    print(f"  Accuracy  : {acc:.4f}%")
    print(f"  Precision : {precision:.4f}%")
    print(f"  Recall    : {recall:.4f}%")
    print(f"  F1-Score  : {f1:.4f}%")
    print(f"  AUC-ROC   : {auc:.4f}%")
    print("\n" + classification_report(all_labels, all_preds,
                                       target_names=class_names, zero_division=0))

    if plot:
        _plot_confusion_matrix(all_labels, all_preds, class_names,
                               model_name, save_dir)
        _plot_roc_curves(all_labels, all_probs, class_names,
                         model_name, save_dir)

    return metrics


def _plot_confusion_matrix(labels, preds, class_names, model_name, save_dir):
    cm = confusion_matrix(labels, preds)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, data, fmt, title in zip(
        axes,
        [cm, cm_norm],
        ['d', '.2f'],
        [f'Matrice de Confusion — {model_name}',
         f'Matrice Normalisée — {model_name}']
    ):
        sns.heatmap(data, annot=True, fmt=fmt, cmap='Blues',
                    xticklabels=class_names, yticklabels=class_names, ax=ax)
        ax.set_xlabel('Prédit'); ax.set_ylabel('Réel')
        ax.set_title(title)

    plt.tight_layout()
    plt.savefig(f"{save_dir}/{model_name}_confusion_matrix.png",
                dpi=150, bbox_inches='tight')
    plt.show()  # Display the plot
    plt.close() # Close the plot to free memory
    print(f"  Matrice de confusion sauvegardée")


def _plot_roc_curves(labels, probs, class_names, model_name, save_dir):
    y_bin = label_binarize(labels, classes=list(range(len(class_names))))
    if y_bin.shape[1] == 1:
        return

    plt.figure(figsize=(10, 7))
    colors = plt.cm.Set1(np.linspace(0, 1, len(class_names)))

    for i, (name, color) in enumerate(zip(class_names, colors)):
        if y_bin[:, i].sum() == 0:
            continue
        fpr, tpr, _ = roc_curve(y_bin[:, i], probs[:, i])
        roc_auc = auc_score(fpr, tpr)
        plt.plot(fpr, tpr, color=color, lw=2,
                 label=f'{name} (AUC = {roc_auc:.3f})')

    plt.plot([0, 1], [0, 1], 'k--', lw=1)
    plt.xlim([0, 1]); plt.ylim([0, 1.02])
    plt.xlabel('Taux de Faux Positifs')
    plt.ylabel('Taux de Vrais Positifs')
    plt.title(f'Courbes ROC — {model_name}')
    plt.legend(loc='lower right')
    plt.tight_layout()
    plt.savefig(f"{save_dir}/{model_name}_roc_curves.png",
                dpi=150, bbox_inches='tight')
    plt.show()  # Display the plot
    plt.close() # Close the plot to free memory
    print(f"  Courbes ROC sauvegardées")


# ──────────────────────────────────────────────────
# 4. VISUALISATION DE L'HISTORIQUE D'ENTRAÎNEMENT
# ──────────────────────────────────────────────────

def plot_training_history(history, model_name, save_dir='results'):
    """Courbes de loss et d'accuracy train/val"""
    os.makedirs(save_dir, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(history['train_loss'], label='Train Loss', color='blue')
    axes[0].plot(history['val_loss'],   label='Val Loss',   color='red',  linestyle='--')
    axes[0].set_title(f'Loss — {model_name}')
    axes[0].set_xlabel('Époque'); axes[0].set_ylabel('Loss')
    axes[0].legend(); axes[0].grid(True, alpha=0.3)

    axes[1].plot(history['train_acc'], label='Train Acc', color='blue')
    axes[1].plot(history['val_acc'],   label='Val Acc',   color='red',  linestyle='--')
    axes[1].set_title(f'Accuracy — {model_name}')
    axes[1].set_xlabel('Époque'); axes[1].set_ylabel('Accuracy (%)')
    axes[1].legend(); axes[1].grid(True, alpha=0.3)

    plt.suptitle(f'Historique d\'entraînement — {model_name}', fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{save_dir}/{model_name}_training_history.png",
                dpi=150, bbox_inches='tight')
    plt.show()  # Display the plot
    plt.close() # Close the plot to free memory


# ──────────────────────────────────────────────────
# 5. COMPARAISON DE TOUS LES MODÈLES
# ──────────────────────────────────────────────────

def compare_models(results_list, save_dir='results'):
    """
    Génère un tableau et graphiques comparatifs de tous les modèles.

    Args:
        results_list : liste de dicts retournés par evaluate_model()
    """
    os.makedirs(save_dir, exist_ok=True)
    df = pd.DataFrame(results_list)
    df = df.sort_values('f1_score', ascending=False).reset_index(drop=True)

    # Sauvegarde CSV
    df.to_csv(f"{save_dir}/models_comparison.csv", index=False)
    print("\n" + "=" * 70)
    print("  TABLEAU COMPARATIF DES MODÈLES")
    print("=" * 70)
    print(df.to_string(index=False))

    # Graphique comparatif
    metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'auc_roc']
    fig, axes = plt.subplots(1, len(metrics), figsize=(22, 6))

    for ax, metric in zip(axes, metrics):
        bars = ax.barh(df['model'], df[metric],
                       color=plt.cm.viridis(np.linspace(0.3, 0.9, len(df))))
        ax.set_xlabel('%')
        ax.set_title(metric.replace('_', ' ').title())
        ax.set_xlim([df[metric].min() - 2, 100.5])
        ax.axvline(x=df[metric].mean(), color='red', linestyle='--',
                   alpha=0.5, label='Moyenne')

        # Annotations
        for bar, val in zip(bars, df[metric]):
            ax.text(val + 0.2, bar.get_y() + bar.get_height() / 2,
                    f'{val:.1f}', va='center', fontsize=8)

    plt.suptitle('Comparaison des Modèles IDS', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig(f"{save_dir}/models_comparison.png", dpi=150, bbox_inches='tight')
    plt.show()  # Display the plot
    plt.close() # Close the plot to free memory
    print(f"\n Comparaison sauvegardée: {save_dir}/models_comparison.png")

    return df


# ──────────────────────────────────────────────────
# 6. CALCUL DES POIDS DE CLASSES (anti-déséquilibre)
# ──────────────────────────────────────────────────

def compute_class_weights(y_train: np.ndarray, num_classes: int) -> torch.Tensor:
    """Calcule les poids inversement proportionnels à la fréquence de chaque classe."""
    counts = np.bincount(y_train, minlength=num_classes)
    weights = 1.0 / (counts + 1e-6)
    weights = weights / weights.sum() * num_classes
    return torch.FloatTensor(weights)


# ──────────────────────────────────────────────────
# 7. PIPELINE PRINCIPAL COMPLET
# ──────────────────────────────────────────────────

def run_full_experiment(train_loader, val_loader, test_loader,
                        models_dict, class_names,
                        num_epochs=50, lr=1e-3, patience=10,
                        save_dir='results', y_train=None):
    """
    Entraîne et évalue tous les modèles fournis.

    Args:
        models_dict : {'model_name': model_instance, ...}
        class_names : liste des noms de classes
        y_train     : labels d'entraînement (pour class weights)

    Returns:
        results_df : DataFrame comparatif
        histories  : dict des historiques par modèle
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n  Device: {device}")
    print(f" Modèles à entraîner: {list(models_dict.keys())}")

    # Poids de classes
    class_weights = None
    if y_train is not None:
        class_weights = compute_class_weights(y_train, len(class_names))
        print(f"  ⚖️  Class weights: {class_weights.numpy().round(3)}")

    all_results = []
    histories   = {}

    for name, model in models_dict.items():
        print(f"\n{'─'*60}")
        print(f"  Modèle : {name}")
        print(f"  Paramètres : {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

        # Entraînement
        history = train_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            num_epochs=num_epochs,
            lr=lr,
            patience=patience,
            device=device,
            model_name=name,
            save_dir=f"{save_dir}/checkpoints",
            class_weights=class_weights
        )
        histories[name] = history

        # Courbes d'entraînement
        plot_training_history(history, name, save_dir)

        # Évaluation
        metrics = evaluate_model(
            model=model,
            test_loader=test_loader,
            class_names=class_names,
            device=device,
            model_name=name,
            plot=True,
            save_dir=save_dir
        )
        metrics['training_time'] = round(history.get('training_time', 0), 1)
        all_results.append(metrics)

    # Comparaison finale
    results_df = compare_models(all_results, save_dir)

    # Sauvegarde JSON
    with open(f"{save_dir}/all_results.json", 'w') as f:
        json.dump(all_results, f, indent=2)

    return results_df, histories
