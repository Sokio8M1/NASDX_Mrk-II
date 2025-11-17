#!/usr/bin/env python3
"""
Visual Voice Activity Indicator
Displays animated circular orb in new terminal window
"""

import asyncio
import subprocess
import sys
import math
import os
from pathlib import Path

INDICATOR_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Jarvis Voice Activity</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #0a0a0a;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            overflow: hidden;
        }
        
        #canvas {
            background: transparent;
        }
        
        .status {
            position: absolute;
            bottom: 20px;
            color: #00ffff;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            text-align: center;
            width: 100%;
        }
    </style>
</head>
<body>
    <canvas id="canvas"></canvas>
    <div class="status" id="status">LISTENING...</div>
    
    <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const status = document.getElementById('status');
        
        canvas.width = 400;
        canvas.height = 400;
        
        let isListening = false;
        let isSpeaking = false;
        let amplitude = 0;
        let phase = 0;
        
        // WebSocket connection to main process
        let ws = null;
        
        function connectWebSocket() {
            ws = new WebSocket('ws://localhost:8765');
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                isListening = data.listening;
                isSpeaking = data.speaking;
                status.textContent = isSpeaking ? 'SPEAKING...' : 'LISTENING...';
            };
            
            ws.onclose = () => {
                setTimeout(connectWebSocket, 1000);
            };
        }
        
        connectWebSocket();
        
        function drawOrb() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            const centerX = canvas.width / 2;
            const centerY = canvas.height / 2;
            const baseRadius = 80;
            
            phase += 0.05;
            
            // Pulsating effect
            const pulseRadius = baseRadius + Math.sin(phase) * 10;
            
            // Outer glow
            const gradient = ctx.createRadialGradient(
                centerX, centerY, 0,
                centerX, centerY, pulseRadius + 40
            );
            
            if (isSpeaking) {
                gradient.addColorStop(0, 'rgba(0, 255, 255, 0.8)');
                gradient.addColorStop(0.5, 'rgba(0, 200, 255, 0.4)');
                gradient.addColorStop(1, 'rgba(0, 100, 255, 0)');
            } else {
                gradient.addColorStop(0, 'rgba(0, 255, 150, 0.6)');
                gradient.addColorStop(0.5, 'rgba(0, 200, 100, 0.3)');
                gradient.addColorStop(1, 'rgba(0, 100, 50, 0)');
            }
            
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(centerX, centerY, pulseRadius + 40, 0, Math.PI * 2);
            ctx.fill();
            
            // Inner orb
            ctx.fillStyle = isSpeaking ? '#00ffff' : '#00ff88';
            ctx.beginPath();
            ctx.arc(centerX, centerY, pulseRadius, 0, Math.PI * 2);
            ctx.fill();
            
            // Animated ring
            ctx.strokeStyle = isSpeaking ? 'rgba(0, 255, 255, 0.8)' : 'rgba(0, 255, 150, 0.8)';
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.arc(centerX, centerY, pulseRadius + 20, 0, Math.PI * 2);
            ctx.stroke();
            
            // Waveform visualization (when speaking)
            if (isSpeaking) {
                ctx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                
                for (let i = 0; i < 360; i += 5) {
                    const angle = (i * Math.PI) / 180;
                    const waveOffset = Math.sin(angle * 3 + phase * 2) * 15;
                    const radius = pulseRadius + waveOffset;
                    const x = centerX + Math.cos(angle) * radius;
                    const y = centerY + Math.sin(angle) * radius;
                    
                    if (i === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                }
                
                ctx.closePath();
                ctx.stroke();
            }
            
            requestAnimationFrame(drawOrb);
        }
        
        drawOrb();
    </script>
</body>
</html>
"""

async def start_voice_indicator():
    """Start visual indicator in new terminal window"""
    
    # Create temp HTML file
    temp_dir = Path("/tmp") if os.name != "nt" else Path(os.environ["TEMP"])
    html_path = temp_dir / "jarvis_indicator.html"
    
    with open(html_path, "w") as f:
        f.write(INDICATOR_HTML)
    
    # Platform-specific terminal launch
    if sys.platform == "win32":
        # Windows - new window with browser
        process = subprocess.Popen([
            "start", "cmd", "/c",
            f"start chrome --new-window --app=file:///{html_path}"
        ], shell=True)
    
    elif sys.platform == "darwin":
        # macOS - new Terminal window
        process = subprocess.Popen([
            "osascript", "-e",
            f'tell app "Terminal" to do script "open {html_path}"'
        ])
    
    else:
        # Linux - try gnome-terminal or xterm
        try:
            process = subprocess.Popen([
                "gnome-terminal", "--",
                "python3", "-m", "http.server", "--directory", temp_dir.as_posix()
            ])
        except:
            process = subprocess.Popen([
                "xterm", "-e",
                f"python3 -m http.server --directory {temp_dir}"
            ])
    
    return process

# WebSocket server for indicator communication
class IndicatorServer:
    """WebSocket server to communicate with indicator"""
    
    def __init__(self):
        self.clients = set()
        self.listening = False
        self.speaking = False
    
    async def handler(self, websocket, path):
        self.clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
    
    async def broadcast_state(self):
        """Send current state to all connected indicators"""
        if self.clients:
            message = {
                'listening': self.listening,
                'speaking': self.speaking
            }
            await asyncio.gather(
                *[client.send(str(message)) for client in self.clients],
                return_exceptions=True
            )
    
    def set_listening(self, state):
        self.listening = state
        asyncio.create_task(self.broadcast_state())
    
    def set_speaking(self, state):
        self.speaking = state
        asyncio.create_task(self.broadcast_state())

indicator_server = IndicatorServer()

async def start_indicator_server():
    """Start WebSocket server for indicator"""
    import websockets
    
    async with websockets.serve(indicator_server.handler, "localhost", 8765):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    # Test the indicator standalone
    asyncio.run(start_voice_indicator())
    print("Voice indicator started. Press Ctrl+C to stop.")
    try:
        asyncio.run(start_indicator_server())
    except KeyboardInterrupt:
        print("\nIndicator stopped.")