from flask import Flask, jsonify, render_template
import requests
from requests.auth import HTTPBasicAuth
import urllib3
from datetime import datetime

# desactiva advertencias SSL solo para pruebas
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

#configuracion del router csr
ROUTER = {
     "host" : "192.168.149.10",
     "port" : 443,
     "user" : "admin",
     "pass" : "admin"
}

HEADERS = {
    "Accept": "application/yang-data+json"
}

def get_interfaces():
    url = f"https://{ROUTER['host']}:{ROUTER['port']}/restconf/data/ietf-interfaces:interfaces"
    response = requests.get(url, auth=HTTPBasicAuth(ROUTER['user'], ROUTER['pass']),
                            headers=HEADERS, verify=False)
    
    interfaces = []
    if response.status_code == 200:
        data = response.json()
        for iface in data.get("ietf-interfaces:interfaces", {}).get("interface", []):
            interfaces.append({
                "name": iface.get("name", "N/A"),
                "admin_status": iface.get("enabled", "N/A"),
                "oper_status": iface.get("ietf-ip:ipv4", {}).get("enabled", "N/A"),
                "ipv4": iface.get("ietf-ip:ipv4", {}).get("address", [{}])[0].get("ip", "N/A") if iface.get("ietf-ip:ipv4", {}).get("address") else "N/A",
                "ipv6": iface.get("ietf-ip:ipv6", {}).get("address", [{}])[0].get("ip", "N/A") if iface.get("ietf-ip:ipv6", {}).get("address") else "N/A"
            })
    else:
        print("Error interfaces:", response.status_code, response.text)
    
    return interfaces


def get_ospf_neighbors():
    url = f"https://{ROUTER['host']}:{ROUTER['port']}/restconf/data/Cisco-IOS-XE-ospf-oper:ospf-oper-data"
    response = requests.get(url, auth=HTTPBasicAuth(ROUTER['user'], ROUTER['pass']),
                            headers=HEADERS, verify=False)
    
    neighbors = []
    if response.status_code == 200:
        data = response.json()
        try:
            instances = data["Cisco-IOS-XE-ospf-oper:ospf-oper-data"]["ospf-state"]["ospf-instance"]
            for instance in instances:
                for area in instance.get("ospf-area", []):
                    for iface in area.get("ospf-interface", []):
                        for nbr in iface.get("ospf-neighbor", []):
                            neighbors.append({
                                "router_id": nbr.get("neighbor-id", "N/A"),
                                "interface": iface.get("name", "N/A"),
                                "state": nbr.get("state", "N/A"),
                                "neighbor_address": nbr.get("address", "N/A")
                            })
        except KeyError as e:
            print("Error al procesar OSPF:", e)
    else:
        print("Error OSPF:", response.status_code, response.text)
    
    return neighbors


def get_routes():
    url = f"https://{ROUTER['host']}:{ROUTER['port']}/restconf/data/ietf-routing:routing-state"
    response = requests.get(url, auth=HTTPBasicAuth(ROUTER['user'], ROUTER['pass']),
                            headers=HEADERS, verify=False)
    
    routes = []
    if response.status_code == 200:
        try:
            data = response.json()
            ribs = data["ietf-routing:routing-state"]["routing-instance"][0]["ribs"]["rib"]
            for rib in ribs:
                for route in rib.get("routes", {}).get("route", []):
                    routes.append({
                        "prefix": route.get("destination-prefix", "N/A"),
                        "next_hop": route.get("next-hop", {}).get("outgoing-interface", "N/A"),
                        "metric": route.get("metric", "N/A"),
                        "source_protocol": route.get("source-protocol", "N/A")
                    })
        except KeyError as e:
            print("Error al procesar rutas:", e)
    else:
        print("Error rutas:", response.status_code, response.text)
    
    return routes


@app.route("/")
def index():
    interfaces = get_interfaces()
    ospf_neighbors = get_ospf_neighbors()
    routes = get_routes()
    return render_template("index.html",
                           interfaces=interfaces,
                           ospf_neighbors=ospf_neighbors,
                           routes=routes,
                           last_update=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))


if __name__ == "__main__":
    app.run(debug=True)