import json
import paho.mqtt.client as mqtt
import redis
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse

r = redis.Redis(host="localhost", port=6379)

def on_connect(c, u, flags, rc, props):
    print("bridge connected to MQTT", rc)
    c.subscribe("grid/+/telemetry")
    c.subscribe("grid/+/status")
    c.subscribe("grid/+/ack")
    c.subscribe("grid/+/event")
    

def on_message(c, u, msg):
    parts = msg.topic.split("/")
    dev, kind = parts[1], parts[2]
    text = msg.payload.decode()
    try:
        data = json.loads(text)
    except Exception:
        data = text
    frame = {"device": dev, "type": kind, "data": data}
    r.publish("device_live:" + dev, json.dumps(frame))

mc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bridge")
mc.on_connect = on_connect
mc.on_message = on_message
mc.connect("localhost", 1883)
mc.loop_start()

app = FastAPI()

PAGE = """<html><body>
<h3>Live device data</h3>
<pre id="o"></pre>
<script>
const ws = new WebSocket("ws://localhost:8000/ws/devices/dev_01");
ws.onmessage = e => {
  const o = document.getElementById("o");
  o.textContent = e.data + "\\n" + o.textContent;
};
</script>
</body></html>"""

@app.get("/")
def home():
    return HTMLResponse(PAGE)

@app.websocket("/ws/devices/{dev}")
async def ws_endpoint(websocket: WebSocket, dev: str):
    await websocket.accept()
    ar = aioredis.Redis(host="localhost", port=6379)
    ps = ar.pubsub()
    await ps.subscribe("device_live:" + dev)
    try:
        while True:
            m = await ps.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if m:
                await websocket.send_text(m["data"].decode())
    except Exception:
        pass
    finally:
        await ps.close()
        await ar.close()