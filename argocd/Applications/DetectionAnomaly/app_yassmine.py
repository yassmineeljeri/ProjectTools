from flask import Flask, request, jsonify
import json
import pandas as pd
import pickle
import re
import requests
from apscheduler.schedulers.background import BackgroundScheduler

import os

SLACK_WEBHOOK_URL = os.getenv("SLACK-WEBHOOK-URL")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/rf_model.pkl")
SCALER_PATH = os.getenv("SCALER_PATH", "/app/robust_scaler.pkl")

LOKI_URL  = os.getenv("LOKI_URL", "https://grafanaloki.devops-tool.com/loki/api/v1/query_range")
LOKI_USER = os.getenv("LOKI_USER")
LOKI_PASS = os.getenv("LOKI_PASS")

app = Flask(__name__)

print("🔵 Starting app.py...")
print("🔵 Loading model from:", MODEL_PATH)

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print("🟢 Model loaded successfully!")
except Exception as e:
    print("🔴 ERROR loading model:", e)
try:
    with open(SCALER_PATH, "rb") as f:
        robust_scaler = pickle.load(f)
    print("🟢 RobustScaler loaded successfully!")
except Exception as e:
    print("🔴 ERROR loading RobustScaler:", e)


def fetch_loki_logs():
    print("🌍 Fetching logs from Grafana Loki...")

    try:
        end = int(pd.Timestamp.utcnow().timestamp()) * 1_000_000_000
        start = (int(pd.Timestamp.utcnow().timestamp()) - 90) * 1_000_000_000  # last 5 min


        query = '{namespace="istio-system", pod=~"ztunnel-.*"} | json | line_format "{{.message}}" | logfmt | line_format "src={{.src_workload}},dst={{.dst_workload}},src_ns={{.src_namespace}},dst_ns={{.dst_namespace}},direction={{.direction}},bytes_sent={{.bytes_sent}},bytes_recv={{.bytes_recv}},duration={{.duration}}" | dst_namespace=~"backend-ns|databases|frontend-ns|opentelemetry|istio-system" | src_namespace=~"backend-ns|databases|frontend-ns|opentelemetry|istio-system" | keep src_workload, dst_workload, src_namespace, dst_namespace, dst_service, direction, bytes_sent, bytes_recv, duration'

        params = {
            "query": query,
            "start": start,
            "end": end,
            "limit": 1000
        }

        headers = {
            "foo": "bar",
            "X-Scope-OrgID": "foo"
        }

        response = requests.get(
            LOKI_URL,
            params=params,
            headers=headers,
            auth=(LOKI_USER, LOKI_PASS),
            verify=True
        )

        response.raise_for_status()
        loki_json = response.json()

        print("🟢 Logs fetched successfully!")
        return loki_json

    except Exception as e:
        print("❌ ERROR fetching logs:", e)
        return None



@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200



# ------------------------
# Encoding maps
# ------------------------
label_map_src = {
   'backdoor-shell': 0,
    'book-services-deployment': 1,
    'book-transaction-service-deployment': 2,
    'coredns': 3,
    'crypto-miner': 4,
    'feedback-service-deployment': 5,
    'frontend': 6,
    'istio-ingress': 7,
    'malicious-api-gateway': 8,
    'malicious-c2-server': 9,
    'metrics-server': 10,
    'mysql-books': 11,
    'mysql-feedbacks': 12,
    'mysql-transactions': 13,
    'otel-collector-opentelemetry-collector': 14,
    'port-scanner': 15,
    'security-service-deployment': 16,
    'unknown-ext-svc': 17,
    'upload-file-service-deployment': 18
}

label_map_dst = {
    'backdoor-shell': 0,
    'book-services-deployment': 1,
    'book-transaction-service-deployment': 2,
    'coredns': 3,
    'crypto-miner': 4,
    'feedback-service-deployment': 5,
    'frontend': 6,
    'istiod': 7,
    'malicious-api-gateway': 8,
    'metrics-server': 9,
    'mysql-books': 10,
    'mysql-feedbacks': 11,
    'mysql-transactions': 12,
    'otel-collector-opentelemetry-collector': 13,
    'security-service-deployment': 14,
    'unknown-ext-svc': 15,
    'upload-file-service-deployment': 16
}

namespace_map = {
     'backend-ns': 0,
    'databases': 1,
    'external': 2,
    'frontend-ns': 3,
    'istio-system': 4,
    'kube-system': 5,
    'opentelemetry': 6
}

direction_map = {'inbound': 0, 'outbound': 1}


# ------------------------
# Parse Loki result
# ------------------------
def parse_loki_result(loki_json):

    rows = []

    for item in loki_json["data"]["result"]:
        timestamp = item["values"][0][0]
        values_str = item["values"][0][1]

        kv = {}
        for pair in values_str.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                kv[k] = v

        src_raw = kv.get("src", "")
        dst_raw = kv.get("dst", "")

        src_w = re.sub(r"-[a-z0-9]{5,}-[a-z0-9]{4,}$", "", src_raw)
        dst_w = re.sub(r"-[a-z0-9]{5,}-[a-z0-9]{4,}$", "", dst_raw)

        raw_duration = kv.get("duration", "0")
        cleaned_duration = re.sub(r"[a-zA-Z]+", "", raw_duration)

        duration = float(cleaned_duration) if cleaned_duration else 0.0

        row = {
            "timestamp": timestamp,
            "src_row": src_raw,
            "dst_row": dst_raw,
            "src_workload": src_w,
            "dst_workload": dst_w,
            "src_ns": kv.get("src_ns", ""),
            "dst_ns": kv.get("dst_ns", ""),
            "direction": kv.get("direction", ""),
            "bytes_sent": int(kv.get("bytes_sent", 0)),
            "bytes_recv": int(kv.get("bytes_recv", 0)),
            "duration": duration
        }

        rows.append(row)

    return pd.DataFrame(rows)


@app.route("/")
def home():
    return "API is running! Use /predict to test your model."


def send_slack_alert(message):
    payload = {"text": message}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
        print("📨 Slack alert sent!")
    except Exception as e:
        print("❌ Failed to send Slack alert:", e)


# ------------------------
# 2️⃣ REPLACE JSON LOCAL → FETCH LOKI
# ------------------------
def predict_from_local_json():

    print("\n📡 Fetching live Loki logs instead of local JSON...")

    loki_json = fetch_loki_logs()
    if loki_json is None:
        print("❌ No logs fetched. Skipping prediction.")
        return

    try:
        df = parse_loki_result(loki_json)

        # ---------------------------------------------
        # 🧩 1) DETECT UNKNOWN PODS BEFORE PREDICTION
        # ---------------------------------------------
        KNOWN_WORKLOADS = {
            "istio-ingress",
            "frontend",
            "book-services-deployment",
            "book-transaction-service-deployment",
            "config-service-deployment",
            "feedback-service-deployment",
            "kafka",
            "notification-service-deployment",
            "security-service-deployment",
            "upload-file-service-deployment",
            "mysql-books",
            "mysql-feedbacks",
            "mysql-transactions",
            "mongo-file",
            "mongo-notifications",
            "otel-collector-opentelemetry-collector",
            "zookeeper",
            "bsn-cert-refresher"
        }

        unknown_df = df[~df["src_workload"].isin(KNOWN_WORKLOADS)]

        # Send alert for each unknown pod
        for _, row in unknown_df.iterrows():
            msg = (
                f"🚨 *MALICIOUS TRAFFIC DETECTED!* 🚨\n"
                f"🆕 *NEW POD DETECTED!* 🚨\n"
                f"• Timestamp: {row['timestamp']}\n"
                f"• Source: {row['src_row']}\n"
                f"• Destination: {row['dst_row']}\n"
                f"• Namespace: {row['src_ns']} → {row['dst_ns']}\n"
                f"• Direction: {row['direction']}\n"
                f"• Bytes sent: {row['bytes_sent']}\n"
                f"• Bytes recv: {row['bytes_recv']}\n"
                f"• Duration: {row['duration']}\n"
            )
            send_slack_alert(msg)

        # Remove unknown pods — do NOT predict on them
        df = df[df["src_workload"].isin(KNOWN_WORKLOADS)]

        if df.empty:
            print("⚠️ All entries were unknown pods — no ML predictions executed.")
            return

        # ---------------------------------------------
        # 🧩 2) NORMAL ENCODING + PREDICTIONS
        # ---------------------------------------------
        # (Your duplicate line was removed)

        # ---------------------------------------------
        # 2) ENCODING
        # ---------------------------------------------
        df["src_workload_encoded"] = df["src_workload"].map(label_map_src).fillna(-1)
        df["dst_workload_encoded"] = df["dst_workload"].map(label_map_dst).fillna(-1)
        df["src_ns_encoded"] = df["src_ns"].map(namespace_map).fillna(-1)
        df["dst_ns_encoded"] = df["dst_ns"].map(namespace_map).fillna(-1)
        df["direction_encoded"] = df["direction"].map(direction_map).fillna(-1)

        # ---------------------------------------------
        # 🔥 3) SCALE numeric columns USING LOADED ROBUST SCALER
        # ---------------------------------------------
        scale_cols = ["bytes_sent", "bytes_recv", "duration"]

        try:
            df[scale_cols] = robust_scaler.transform(df[scale_cols])
            print("🟢 Scaling applied successfully!")
        except Exception as e:
            print("❌ ERROR applying RobustScaler:", e)

        # ---------------------------------------------
        # 4) PREDICTION
        # ---------------------------------------------
        features = [
            "bytes_sent", "bytes_recv", "duration",
            "src_workload_encoded", "dst_workload_encoded",
            "src_ns_encoded", "dst_ns_encoded",
            "direction_encoded"
        ]

        X = df[features]
        preds = model.predict(X)
        probas = model.predict_proba(X).max(axis=1)

        df["prediction"] = preds
        df["probability"] = probas

        print("\n🔮 LIVE PREDICTIONS:")
        print(df[[ 
            "timestamp", "src_row", "dst_row",
            "src_ns", "dst_ns", "direction",
            "bytes_sent", "bytes_recv",
            "duration", "prediction", "probability"
        ]])

        # ---------------------------------------------
        # 🧩 3) SEND MALICIOUS TRAFFIC ALERTS
        # ---------------------------------------------
        alert_count = 0
        pred = 0

        for _, row in df.iterrows():
            if row["prediction"] == 0:
                pred += 1

                msg = (
                    f"🚨 *MALICIOUS TRAFFIC DETECTED!* 🚨\n"
                    f"• Timestamp: {row['timestamp']}\n"
                    f"• Source: {row['src_row']}\n"
                    f"• Destination: {row['dst_row']}\n"
                    f"• Namespace: {row['src_ns']} → {row['dst_ns']}\n"
                    f"• Direction: {row['direction']}\n"
                    f"• Bytes sent: {row['bytes_sent']}\n"
                    f"• Bytes recv: {row['bytes_recv']}\n"
                    f"• Duration: {row['duration']}\n"
                )
                send_slack_alert(msg)
                alert_count += 1

        print(f"🔢 Total pred: {pred}")
        print(f"🔢 Total Slack alerts sent: {alert_count}")

    except Exception as e:
        print("❌ ERROR processing Loki logs:", e)


def run_periodic_pipeline():
    print("\n⏳ Running scheduled pipeline (every 1 minutes)...")
    try:
        predict_from_local_json()
        print("✔️ Scheduled pipeline finished successfully.")
    except Exception as e:
        print("❌ Error in scheduled pipeline:", e)


if __name__ == "__main__":
    predict_from_local_json()  # Run once at startup

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_periodic_pipeline, "interval", minutes=1)
    scheduler.start()

    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)
