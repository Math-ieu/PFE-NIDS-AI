import os
import json
import asyncio
import boto3
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import datetime

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

# Dynamic Private IP to Machine & Service Resolver
class IPResolver:
    def __init__(self, region=REGION):
        self.region = region
        self.ip_map = {}
        self.last_fetched = 0
        self.ttl = 60 # Refresh every 1 minute to stay up to date
        self.ec2 = boto3.client('ec2', region_name=self.region)

    def get_mapping(self):
        now = time.time()
        if now - self.last_fetched > self.ttl:
            try:
                print("[*] Resolving Private/Public IPs from AWS EC2...", flush=True)
                response = self.ec2.describe_instances()
                new_map = {}
                for reservation in response.get('Reservations', []):
                    for instance in reservation.get('Instances', []):
                        private_ip = instance.get('PrivateIpAddress')
                        public_ip = instance.get('PublicIpAddress')
                        
                        name = "Unknown"
                        service = "Unknown"
                        for tag in instance.get('Tags', []):
                            if tag['Key'] == 'Name':
                                name = tag['Value']
                            if tag['Key'] == 'Service':
                                service = tag['Value']
                        
                        if private_ip:
                            new_map[private_ip] = {"name": name, "service": service}
                        if public_ip:
                            new_map[public_ip] = {"name": name, "service": service}
                
                # Override Kali Linux Attack Machine role
                for ip, info in new_map.items():
                    if info["name"] == "Kali-Attack":
                        info["service"] = "Attacker"
                
                self.ip_map = new_map
                self.last_fetched = now
            except Exception as e:
                print(f"[!] Error resolving private IPs from EC2: {e}", flush=True)
        return self.ip_map

    def resolve(self, ip):
        if not ip:
            return {"name": "Unknown", "service": "Unknown"}
        mapping = self.get_mapping()
        return mapping.get(ip, {"name": ip, "service": "Unknown"})

resolver = IPResolver(region=REGION)

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
    """Récupère les statistiques globales des attaques, par machine et par service"""
    response = table.scan() # Note: Scan is okay for small PFE scale
    items = response.get('Items', [])
    
    stats_by_type = {}
    stats_by_machine = {}
    stats_by_service = {}
    
    for item in items:
        # Distribution par type d'attaque
        atk_type = item.get('attack_type', 'Unknown')
        stats_by_type[atk_type] = stats_by_type.get(atk_type, 0) + 1
        
        # Distribution par machine victime
        dst_ip = item.get('dst_ip')
        if dst_ip:
            resolved = resolver.resolve(dst_ip)
            machine = resolved["name"]
            service = resolved["service"]
            
            stats_by_machine[machine] = stats_by_machine.get(machine, 0) + 1
            stats_by_service[service] = stats_by_service.get(service, 0) + 1
    
    return {
        "total_alerts": len(items),
        "attack_distribution": stats_by_type,
        "machine_distribution": stats_by_machine,
        "service_distribution": stats_by_service,
        "last_update": datetime.now().isoformat()
    }

@app.get("/api/alerts/recent")
async def get_recent_alerts(limit: int = 20):
    """Récupère les dernières alertes enrichies"""
    response = table.scan() 
    items = response.get('Items', [])
    # Tri manuel pour le PFE
    sorted_items = sorted(items, key=lambda x: x['timestamp'], reverse=True)
    
    enriched_items = []
    for item in sorted_items[:limit]:
        src_resolved = resolver.resolve(item.get('src_ip'))
        dst_resolved = resolver.resolve(item.get('dst_ip'))
        
        enriched = dict(item)
        enriched['src_machine'] = src_resolved['name']
        enriched['dst_machine'] = dst_resolved['name']
        enriched['dst_service'] = dst_resolved['service']
        enriched_items.append(enriched)
        
    return enriched_items

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.active_connections.append(websocket)
    try:
        # Boucle de surveillance DynamoDB pour le mode "Push"
        last_timestamp = int(datetime.now().timestamp())
        while True:
            response = table.scan()
            items = response.get('Items', [])
            new_alerts = [i for i in items if int(i['timestamp']) > last_timestamp]
            
            # Trier pour envoyer par ordre chronologique
            sorted_new = sorted(new_alerts, key=lambda x: int(x['timestamp']))
            
            for alert in sorted_new:
                src_resolved = resolver.resolve(alert.get('src_ip'))
                dst_resolved = resolver.resolve(alert.get('dst_ip'))
                
                enriched = dict(alert)
                enriched['src_machine'] = src_resolved['name']
                enriched['dst_machine'] = dst_resolved['name']
                enriched['dst_service'] = dst_resolved['service']
                
                await manager.broadcast(json.dumps(enriched))
                
                if int(alert['timestamp']) > last_timestamp:
                    last_timestamp = int(alert['timestamp'])
            
            await asyncio.sleep(2) # Polling toutes les 2 secondes
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket Error] {e}")
        try:
            manager.disconnect(websocket)
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

