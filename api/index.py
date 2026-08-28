# api/index.py
from flask import Flask, request, jsonify
import json
import os
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# MANHATTAN_ENV maps a short environment key (shown in the login dropdown) to its
# Manhattan API host. The auth host is derived by inserting "-auth" before the
# host's first dot (e.g. salep.sce.manh.com -> salep-auth.sce.manh.com), which is
# Manhattan's own documented host-pairing convention. Defaults cover the two known
# environments so the app works even before this var is set in Vercel.
DEFAULT_MANHATTAN_ENV = {"SALEP": "salep.sce.manh.com", "SALES3": "sales3.sce.manh.com"}
try:
    ENVIRONMENTS = json.loads(os.getenv("MANHATTAN_ENV", "")) or DEFAULT_MANHATTAN_ENV
except (json.JSONDecodeError, TypeError):
    print("[config] MANHATTAN_ENV is not valid JSON; falling back to defaults")
    ENVIRONMENTS = DEFAULT_MANHATTAN_ENV

# Environments where the org/facility prefix is the part of the username BEFORE the
# "@" (uppercased) rather than after -- e.g. sales3's "masc@sdt-demo" -> org "MASC".
# Confirmed against sales3 specifically; any environment not listed here defaults to
# the salep-style convention (org is the part AFTER the "@", e.g. "demoweb@SS-DEMO" -> "SS-DEMO").
ORG_BEFORE_AT_ENVIRONMENTS = {"SALES3"}

PASSWORD = os.getenv("MANHATTAN_PASSWORD")
CLIENT_ID = "omnicomponent.1.0.0"
CLIENT_SECRET = os.getenv("MANHATTAN_SECRET")

USAGE_INGEST_URL = os.getenv("MANHATTAN_USAGE_INGEST_URL", "").strip()
USAGE_INGEST_SECRET = os.getenv("MANHATTAN_USAGE_INGEST_SECRET", "").strip()
APP_NAME = "item-generator-app"
APP_VERSION = "1.0.6"


def get_api_host(environment):
    host = ENVIRONMENTS.get((environment or "").strip().upper())
    if not host:
        raise ValueError(f"Unknown environment: {environment}")
    return host


def get_auth_host(environment):
    api_host = get_api_host(environment)
    stack, _, rest = api_host.partition(".")
    return f"{stack}-auth.{rest}"


def derive_org(environment, username):
    """Derive the org/facility prefix used in API headers from the login username."""
    username = (username or "").strip()
    if "@" not in username:
        return username.upper()
    before, after = username.split("@", 1)
    if (environment or "").strip().upper() in ORG_BEFORE_AT_ENVIRONMENTS:
        return before.upper()
    return after.upper()


def _json_body():
    return request.get_json(silent=True) or {}


def _missing_secrets_error():
    if not PASSWORD or not CLIENT_SECRET:
        return "Server misconfigured: MANHATTAN_PASSWORD and MANHATTAN_SECRET must be set in Vercel"
    return None


def forward_usage_event(payload):
    if not USAGE_INGEST_URL:
        print("[usage] MANHATTAN_USAGE_INGEST_URL not set; event not recorded")
        return
    headers = {"Content-Type": "application/json"}
    if USAGE_INGEST_SECRET:
        headers["Authorization"] = f"Bearer {USAGE_INGEST_SECRET}"
    try:
        requests.post(USAGE_INGEST_URL, json=payload, headers=headers, timeout=8)
    except Exception as e:
        print(f"[usage] Forward failed: {e}")


def get_manhattan_token(environment, username):
    url = f"https://{get_auth_host(environment)}/oauth/token"
    data = {
        "grant_type": "password",
        "username": username,
        "password": PASSWORD,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    try:
        r = requests.post(url, data=data, headers=headers, auth=auth, timeout=60, verify=False)
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception as e:
        print(f"[AUTH] Error: {e}")
    return None


def manhattan_headers(org, token):
    facility_id = f"{org.upper()}-DM1"
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "FacilityId": facility_id,
        "selectedOrganization": org.upper(),
        "selectedLocation": facility_id,
    }


def log_api_call(endpoint, method, url, headers=None, payload=None, response=None, status_code=None):
    print("=" * 80)
    print(f"[API_CALL] {method} {endpoint}")
    print("=" * 80)
    print(f"[API_CALL] URL: {url}")
    if headers:
        log_headers = headers.copy()
        if "Authorization" in log_headers:
            log_headers["Authorization"] = "Bearer [REDACTED]"
        print(f"[API_CALL] Headers: {json.dumps(log_headers, indent=2)}")
    if payload:
        print(f"[API_CALL] Payload: {json.dumps(payload, indent=2)}")
    if status_code:
        print(f"[API_CALL] Response Status: {status_code}")
    if response is not None:
        response_str = json.dumps(response, indent=2) if isinstance(response, dict) else str(response)
        if len(response_str) > 2000:
            response_str = response_str[:2000] + "... [TRUNCATED]"
        print(f"[API_CALL] Response: {response_str}")
    print("=" * 80)


@app.route("/api/app_opened", methods=["POST"])
def app_opened():
    print("[APP] Item Copy opened")
    return jsonify({"success": True})


@app.route("/api/environments", methods=["POST"])
def environments():
    """List the configured environment keys for the login dropdown."""
    return jsonify({"success": True, "environments": sorted(ENVIRONMENTS.keys())})


@app.route("/api/auth", methods=["POST"])
def auth():
    config_err = _missing_secrets_error()
    if config_err:
        print(f"[AUTH] {config_err}")
        return jsonify({"success": False, "error": config_err}), 500
    data = _json_body()
    environment = data.get("environment", "").strip()
    username = data.get("username", "").strip()
    if not environment or not username:
        return jsonify({"success": False, "error": "Environment and Username required"})

    try:
        get_api_host(environment)
    except ValueError:
        return jsonify({"success": False, "error": f"Unknown environment: {environment}"})

    org = derive_org(environment, username)

    print(f"[AUTH] Authenticating {username} against {environment} (org: {org})")
    token = get_manhattan_token(environment, username)
    if token:
        print(f"[AUTH] Success for {username} on {environment} (org: {org})")
        return jsonify({"success": True, "token": token, "org": org})
    print(f"[AUTH] Failed for {username} on {environment}")
    return jsonify({"success": False, "error": "Auth failed"})


@app.route("/api/find_item", methods=["POST"])
def find_item():
    data = _json_body()
    environment = data.get("environment", "").strip()
    org = data.get("org", "").strip()
    token = data.get("token", "").strip()
    item_id = data.get("itemId", "").strip()

    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    if not item_id:
        return jsonify({"success": False, "error": "Item ID required"})

    safe_id = item_id.replace("'", "''")
    query = f"ItemId='{safe_id}'"
    try:
        url = f"https://{get_api_host(environment)}/item-master/api/item-master/item/search"
    except ValueError:
        return jsonify({"success": False, "error": f"Unknown environment: {environment}"})
    payload = {"Query": query}
    headers = manhattan_headers(org, token)

    log_api_call("find_item", "POST", url, headers=headers, payload=payload)

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=60, verify=False)
        log_api_call("find_item", "POST", url, response=r.text, status_code=r.status_code)

        if r.status_code not in (200, 201):
            return jsonify({
                "success": False,
                "error": f"Invalid Item - API {r.status_code}: {r.text[:500]}",
            })

        try:
            response_data = r.json()
        except json.JSONDecodeError:
            return jsonify({"success": False, "error": "Invalid Item - Invalid response format"})

        data_list = response_data.get("data") or response_data.get("Data") or []
        if not isinstance(data_list, list):
            data_list = []

        count = len(data_list)
        if count == 0:
            return jsonify({"success": False, "error": "Invalid Item", "count": 0})
        if count > 1:
            ids = [row.get("ItemId") or row.get("itemId") for row in data_list[:5]]
            return jsonify({
                "success": False,
                "error": f"Multiple items found ({count}). Expected exactly one. Examples: {', '.join(str(i) for i in ids if i)}",
                "count": count,
            })

        item_data = data_list[0]
        print(f"[FIND_ITEM] Found item: {item_id}")
        return jsonify({
            "success": True,
            "itemData": item_data,
            "itemId": item_id,
            "count": 1,
        })
    except Exception as e:
        print(f"[FIND_ITEM] {e}")
        return jsonify({"success": False, "error": f"Error finding item: {str(e)}"})


@app.route("/api/create_item", methods=["POST"])
def create_item():
    data = _json_body()
    environment = data.get("environment", "").strip()
    org = data.get("org", "").strip()
    token = data.get("token", "").strip()
    item_data = data.get("itemData")

    if not org or not token:
        return jsonify({"success": False, "error": "ORG and token required"})
    if not item_data:
        return jsonify({"success": False, "error": "Item data required"})

    try:
        url = f"https://{get_api_host(environment)}/item-master/api/item-master/item/save"
    except ValueError:
        return jsonify({"success": False, "error": f"Unknown environment: {environment}"})
    headers = manhattan_headers(org, token)

    log_api_call("create_item", "POST", url, headers=headers, payload=item_data)

    try:
        r = requests.post(url, json=item_data, headers=headers, timeout=60, verify=False)
        log_api_call("create_item", "POST", url, response=r.text, status_code=r.status_code)

        if r.status_code not in (200, 201):
            return jsonify({
                "success": False,
                "error": f"Create failed - API {r.status_code}: {r.text[:500]}",
            })

        try:
            response_data = r.json()
        except json.JSONDecodeError:
            if r.status_code in (200, 201):
                return jsonify({"success": True, "message": "Item created successfully"})
            return jsonify({"success": False, "error": "Invalid response format"})

        new_id = None
        if isinstance(response_data, dict):
            new_id = (
                response_data.get("ItemId")
                or response_data.get("itemId")
                or (response_data.get("data") or {}).get("ItemId")
            )

        print("[CREATE_ITEM] Item created successfully")
        return jsonify({
            "success": True,
            "itemId": new_id,
            "response": response_data,
            "message": "Item created successfully",
        })
    except Exception as e:
        print(f"[CREATE_ITEM] {e}")
        return jsonify({"success": False, "error": f"Error creating item: {str(e)}"})


@app.route("/api/usage-track", methods=["POST"])
def usage_track():
    data = _json_body()
    event_name = data.get("event_name")
    metadata = data.get("metadata", {})
    payload = {
        **metadata,
        "event_name": event_name,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    forward_usage_event(payload)
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
