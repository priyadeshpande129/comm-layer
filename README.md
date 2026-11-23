# Communication Layer
Simulated STM32 device (fake_device.py) and MQTT-to-WebSocket bridge (bridge.py).

Run order:
1. docker start mqtt redis
2. python -m uvicorn bridge:app --port 8000
3. python fake_device.py
4. Open http://localhost:8000# comm-layer
