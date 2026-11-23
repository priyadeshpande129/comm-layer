import json, time, random
import paho.mqtt.client as mqtt

DEV = "dev_01"
T_TEL = f"grid/{DEV}/telemetry"
T_EVT = f"grid/{DEV}/event"
T_CMD = f"grid/{DEV}/command"
T_ACK = f"grid/{DEV}/ack"
T_ST = f"grid/{DEV}/status"

S = {1: {"on": True, "gate": 1.0, "base": 300},
     2: {"on": True, "gate": 1.0, "base": 150},
     3: {"on": True, "gate": 1.0, "base": 50},
     4: {"on": True, "gate": 1.0, "base": 100}}
prio = [1, 2, 3, 4]
sched = {}

def on_connect(c, u, f, rc, p):
    print("connected", rc)
    c.publish(T_ST, "online", qos=1, retain=True)
    c.subscribe(T_CMD, qos=2)

def on_message(c, u, msg):
    cmd = json.loads(msg.payload)
    print("command:", cmd)
    k = cmd.get("cmd")
    s = cmd.get("socket")
    status, reason = "ok", None
    if k == "SOCKET_OFF" and s in S:
        S[s]["on"] = False
    elif k == "SOCKET_ON" and s in S:
        S[s]["on"] = True
    elif k == "MANUAL_GATE_OVERRIDE" and s in S:
        S[s]["gate"] = float(cmd.get("gate", 1.0))
    elif k == "UPDATE_PRIORITIES":
        prio[:] = cmd.get("order", prio)
    elif k == "SET_SCHEDULE" and s in S:
        sched[s] = cmd
    else:
        status, reason = "error", "bad command or socket"
    ack = {"id": cmd.get("id"), "status": status}
    if reason:
        ack["reason"] = reason
    c.publish(T_ACK, json.dumps(ack), qos=1)

c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEV)
c.will_set(T_ST, "offline", qos=1, retain=True)
c.on_connect = on_connect
c.on_message = on_message
c.connect("localhost", 1883)
c.loop_start()

tick = 0
try:
    while True:
        tick += 1
        if tick == 6:
            S[3]["base"] = 1800
            ev = {"ts": int(time.time()), "type": "PLUG_IN",
                  "socket": 3, "power": 1800}
            c.publish(T_EVT, json.dumps(ev), qos=1)
        if tick == 18:
            S[3]["base"] = 50
        out = []
        for i, d in S.items():
            p = 0
            if d["on"]:
                p = int(d["base"] * d["gate"] + random.randint(-10, 10))
            if not d["on"]:
                st = "shed"
            elif d["gate"] < 1.0:
                st = "throttled"
            else:
                st = "active"
            out.append({"id": i, "p_avg": p, "p_max": p + 20,
                        "gate": d["gate"], "state": st})
        tel = {"ts": int(time.time()), "vrms_min": 228.5, "sockets": out}
        c.publish(T_TEL, json.dumps(tel))
        time.sleep(5)
except KeyboardInterrupt:
    c.loop_stop()
    c.disconnect()