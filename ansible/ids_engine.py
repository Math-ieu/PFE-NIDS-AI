import os
import json
import torch
import boto3
import numpy as np
import pandas as pd
from nfstream import NFStreamer
from models import AttentionMLP
from datetime import datetime

# CONFIGURATION
MODEL_PATH = "/opt/nids/attention_mlp_best.pth"
REGION = "eu-west-1"
DYNAMODB_TABLE = "NIDS-Alerts"
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
INTERFACE = "vxlan0" # Interface for decapsulated Traffic Mirroring

# Initialize AWS
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)
sqs = boto3.client('sqs', region_name=REGION)

# Model Parameters (CICIDS2017 standard)
INPUT_DIM = 77 
NUM_CLASSES = 15
CLASS_NAMES = [
    'BENIGN', 'Bot', 'DDoS', 'DoS_GoldenEye', 'DoS_Hulk', 
    'DoS_SlowHTTPTest', 'DoS_Slowloris', 'FTP_Patator', 
    'Heartbleed', 'Infiltration', 'PortScan', 'SSH_Patator', 
    'Web_BruteForce', 'Web_SQLInjection', 'Web_XSS'
]

# Load Model
print(f"[*] Loading model from {MODEL_PATH}...", flush=True)
# Note: hidden_dim must be 256 to match the checkpoint saved during training
model = AttentionMLP(INPUT_DIM, NUM_CLASSES, hidden_dim=256)
model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
model.eval()

def send_alert(flow, prediction, confidence):
    alert = {
        'alert_id': f"alert-{int(time.time())}-{flow.id}",
        'timestamp': int(time.time()),
        'src_ip': flow.src_ip,
        'dst_ip': flow.dst_ip,
        'protocol': flow.protocol,
        'attack_type': prediction,
        'confidence': str(round(confidence * 100, 2)),
        'flow_details': json.dumps({
            'duration': flow.bidirectional_duration_ms,
            'bytes': flow.bidirectional_bytes,
            'packets': flow.bidirectional_packets
        })
    }
    
    # Save to DynamoDB
    table.put_item(Item=alert)
    
    # Send to SQS for further processing
    if SQS_QUEUE_URL:
        sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(alert)
        )
    
    print(f"[!] ALERT: {prediction} detected from {flow.src_ip} to {flow.dst_ip} (Conf: {alert['confidence']}%)", flush=True)

def process_stream():
    print(f"[*] Starting NFStreamer on {INTERFACE}...", flush=True)
    streamer = NFStreamer(source=INTERFACE, active_timeout=10, idle_timeout=5)
    
    for flow in streamer:
        print(f"[DEBUG] Captured flow from {flow.src_ip}", flush=True)
        # extraction des 77 features pour le modèle
        # Mapping simplifié basé sur les colonnes standards de CICIDS2017
        features = np.zeros((1, INPUT_DIM))
        
        try:
            # Remplissage des features (indices basés sur l'ordre CICIDS2017 classique)
            features[0, 0] = getattr(flow, 'bidirectional_duration_ms', 0)
            features[0, 1] = getattr(flow, 'bidirectional_packets', 0)
            features[0, 2] = getattr(flow, 'bidirectional_bytes', 0)
            features[0, 3] = getattr(flow, 'src2dst_packets', 0)
            features[0, 4] = getattr(flow, 'src2dst_bytes', 0)
            features[0, 5] = getattr(flow, 'dst2src_packets', 0)
            features[0, 6] = getattr(flow, 'dst2src_bytes', 0)
        except Exception as e:
            print(f"[!] Error extracting features: {e}", flush=True)
            continue

        with torch.no_grad():
            x = torch.FloatTensor(features)
            output = model(x)
            probs = torch.softmax(output, dim=1)
            conf, pred_idx = torch.max(probs, dim=1)
            
            prediction = CLASS_NAMES[pred_idx.item()]
            
            # DEBUG: Log toutes les prédictions dans le journal
            print(f"[*] Flow: {flow.src_ip} -> {flow.dst_ip} | Pred: {prediction} ({conf.item():.2f})", flush=True)
            
            # Seuil de détection (ajusté pour le test)
            if prediction != 'BENIGN' and conf.item() > 0.4:
                send_alert(flow, prediction, conf.item())

if __name__ == "__main__":
    import time
    process_stream()
