# Seeds POOL_SIZE subscribers into MongoDB (DB open5gs, collection subscribers).
# Ported verbatim from the embedded python in overlays/common/subscriber-seed.yaml
# (k8s Job -> compose one-shot service). Reads the same identity env, so provisioned
# subscribers and registered UEs cannot drift. Idempotent: skips if already seeded.
#
# The AUSF/UDM need the security keys and a subscription profile (slice, AMBR, QoS)
# for 5G registration to succeed. Identity values come from the identity env (set in
# compose.yaml); the AMBR/QoS profile is the upstream default. Mongo host is the
# compose service name mongodb:27017.
import os

from bson import ObjectId
from pymongo import MongoClient

mcc, mnc = os.environ["MCC"], os.environ["MNC"]
start = int(os.environ["MSIN_BASE"])
count = int(os.environ["POOL_SIZE"])
# 15-digit IMSI = MCC + MNC + 10-digit MSIN.
imsis = [f"{mcc}{mnc}{start + i:010d}" for i in range(count)]

security = {
    "k": os.environ["KEY"],
    "amf": os.environ["AMF_FIELD"],
    "op": None,
    "opc": os.environ["OPC"],
}
slice_profile = [
    {
        "sst": int(os.environ["SST"]),
        "sd": os.environ["SD"],
        "default_indicator": True,
        "session": [
            {
                "name": "internet",
                "type": 1,
                "pcc_rule": [],
                "ambr": {
                    "uplink": {"value": 1, "unit": 3},
                    "downlink": {"value": 1, "unit": 3},
                },
                "qos": {
                    "index": 9,
                    "arp": {
                        "priority_level": 8,
                        "pre_emption_capability": 1,
                        "pre_emption_vulnerability": 1,
                    },
                },
            }
        ],
    }
]
ue_ambr = {"uplink": {"value": 1, "unit": 3}, "downlink": {"value": 1, "unit": 3}}

db = MongoClient("mongodb://mongodb:27017").open5gs
existing = db["subscribers"].count_documents({})
if existing >= count:
    print("already seeded", existing, "subscribers; skipping")
    raise SystemExit(0)

docs = [
    {
        "_id": ObjectId(),
        "imsi": imsi,
        "subscribed_rau_tau_timer": 12,
        "network_access_mode": 0,
        "subscriber_status": 0,
        "access_restriction_data": 32,
        "slice": slice_profile,
        "ambr": ue_ambr,
        "security": security,
        "schema_version": 1,
        "__v": 0,
    }
    for imsi in imsis
]
db["subscribers"].insert_many(docs)
print("seeded", len(docs), "subscribers")
