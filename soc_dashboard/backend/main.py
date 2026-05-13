import os
import json
import asyncio
import boto3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime
from boto3.dynamodb.conditions import Key

app = FastAPI(title="PFE NIDS SOC Backend")

# CORS configuration for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Configuration
REGION = "eu-west-1"
DYNAMODB_TABLE = "NIDS-Alerts"
dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(DYNAMODB_TABLE)

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.get("/api/stats")
async def get_stats():
    """Récupère les statistiques globales des attaques"""
    response = table.scan() # Note: Scan is okay for small PFE scale
    items = response.get('Items', [])
    
    stats = {}
    for item in items:
        atk_type = item.get('attack_type', 'Unknown')
        stats[atk_type] = stats.get(atk_type, 0) + 1
    
    return {
        "total_alerts": len(items),
        "attack_distribution": stats,
        "last_update": datetime.now().isoformat()
    }

@app.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = 20):
    """Récupère les 20 dernières alertes"""
    # Dans DynamoDB, on trierait normalement par index GSI sur le timestamp
    response = table.scan() 
    items = response.get('Items', [])
    # Tri manuel pour le PFE
    sorted_items = sorted(items, key=lambda x: x['timestamp'], reverse=True)
    return sorted_items[:limit]

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Boucle de surveillance DynamoDB pour le mode "Push"
        last_timestamp = int(datetime.now().timestamp())
        while True:
            # On cherche les nouvelles alertes depuis la dernière boucle
            # Pour un vrai SOC, on utiliserait DynamoDB Streams + Lambda
            # Ici on poll pour rester simple dans le backend SOC
            response = table.scan()
            items = response.get('Items', [])
            new_alerts = [i for i in items if int(i['timestamp']) > last_timestamp]
            
            for alert in new_alerts:
                await manager.broadcast(json.dumps(alert))
                if int(alert['timestamp']) > last_timestamp:
                    last_timestamp = int(alert['timestamp'])
            
            await asyncio.sleep(2) # Polling toutes les 2 secondes
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
