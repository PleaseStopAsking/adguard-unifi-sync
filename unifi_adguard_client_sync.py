#!/usr/bin/env python3
"""
Unifi Adguard Client Sync - This will update Adguard Home with all active client information from Unifi OS.
Using a MAC Address as a primary identifier, this script will sync the IP Addresses and Names so they reflect what is in Unifi OS.

Usage:
    unifi_adguard_client_sync.py \
        --unifi-url URL --unifi-username USER [--unifi-password PW] \
        --adguard-url URL --adguard-username USER [--adguard-password PW] \
        [--ignored-networks NET1 NET2]

Passwords:
    You may supply passwords either via optional CLI flags or environment variables. If a flag is omitted,
    the script will look for UNIFI_PW / ADGUARD_PW. If neither a flag nor environment variable is present,
    the script exits with an error.
"""
__author__ = "PleaseStopAsking"
__maintainer__ = "PleaseStopAsking"
__version__ = "1.0.0"

import os
from datetime import timezone, datetime
import requests
import argparse
from urllib3.exceptions import InsecureRequestWarning
import urllib3
urllib3.disable_warnings(InsecureRequestWarning)


def parse_args():
    parser = argparse.ArgumentParser(
        description=("Sync active client data in Unifi OS with client records in AdGuard. "
                     "Passwords can be provided via flags or environment variables (UNIFI_PW, ADGUARD_PW)."))
    parser.add_argument("--unifi-url", dest="unifi_url", required=False, help="URL of Unifi Server (or set UNIFI_URL)")
    parser.add_argument("--unifi-username", dest="unifi_username", required=False,
                        help="Username of Unifi user (or set UNIFI_USERNAME)")
    parser.add_argument("--unifi-password", dest="unifi_password", required=False, help="Unifi password (or set UNIFI_PW)")
    parser.add_argument("--adguard-url", dest="adguard_url", required=False, help="URL of AdGuard Server (or set ADGUARD_URL)")
    parser.add_argument("--adguard-username", dest="adguard_username", required=False,
                        help="Username of AdGuard user (or set ADGUARD_USERNAME)")
    parser.add_argument("--adguard-password", dest="adguard_password", required=False, help="AdGuard password (or set ADGUARD_PW)")
    parser.add_argument("--ignored-networks", dest="ignored_networks", required=False,
                        help="Comma-delimited list of network names to ignore (e.g., 'Guest,IoT')")
    args = parser.parse_args()

    # fallback to environment variables if flags not supplied
    # allow using environment for all connection parameters
    if args.unifi_url is None:
        args.unifi_url = os.environ.get("UNIFI_URL")
    if args.unifi_username is None:
        args.unifi_username = os.environ.get("UNIFI_USERNAME")
    if args.unifi_password is None:
        args.unifi_password = os.environ.get("UNIFI_PW")
    if args.adguard_url is None:
        args.adguard_url = os.environ.get("ADGUARD_URL")
    if args.adguard_username is None:
        args.adguard_username = os.environ.get("ADGUARD_USERNAME")
    if args.adguard_password is None:
        args.adguard_password = os.environ.get("ADGUARD_PW")
    if args.ignored_networks is None:
        args.ignored_networks = os.environ.get("IGNORED_NETWORKS", "")
    # convert comma-delimited string to list, trimming whitespace; support empty -> []
    if isinstance(args.ignored_networks, str):
        args.ignored_networks = [n.strip() for n in args.ignored_networks.split(",") if n.strip()]

    # validate presence for all required fields
    if not args.unifi_url:
        raise SystemExit("Unifi URL missing: supply --unifi-url or set UNIFI_URL")
    if not args.unifi_username:
        raise SystemExit("Unifi username missing: supply --unifi-username or set UNIFI_USERNAME")
    if not args.unifi_password:
        raise SystemExit("Unifi password missing: supply --unifi-password or set UNIFI_PW")
    if not args.adguard_url:
        raise SystemExit("AdGuard URL missing: supply --adguard-url or set ADGUARD_URL")
    if not args.adguard_username:
        raise SystemExit("AdGuard username missing: supply --adguard-username or set ADGUARD_USERNAME")
    if not args.adguard_password:
        raise SystemExit("AdGuard password missing: supply --adguard-password or set ADGUARD_PW")
    return args


def unifi_login(s: requests.Session, arguments):
    """
    Simple POST request to log in. This will store a cookie in the session cookie jar.
    :param arguments: argparse arguments
    :param s: requests.Session
    :return: None
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "username": arguments.unifi_username,
        "password": arguments.unifi_password
    }
    r = s.post("{}/api/auth/login".format(arguments.unifi_url), headers=headers, json=data, verify=False)
    r.raise_for_status()


def unifi_get_active_clients(s: requests.Session, arguments):
    """
    Simple GET request to retrieve all Active clients from Unifi.
    :param arguments: argparse arguments
    :param s: requests.Session
    :return: dict[str, dict] -> {mac_addr: client-obj}
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    clients = s.get("{}/proxy/network/v2/api/site/default/clients/active".format(arguments.unifi_url), headers=headers, verify=False)
    clients.raise_for_status()
    c = clients.json()
    active_clients = dict()
    for client in c:
        if client.get('network_name') not in arguments.ignored_networks:
            active_clients[client['mac']] = client
    return active_clients


def adguard_login(s: requests.Session, arguments):
    """
    Simple POST request to log in to Adguard with username and password. Adds cookie
    to session cookie jar.
    :param arguments: argparse arguments
    :param s: requests.Session
    :return: None
    """
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {
        "name": arguments.adguard_username,
        "password": arguments.adguard_password
    }
    r = s.post("{}/control/login".format(arguments.adguard_url), headers=headers, json=data)
    r.raise_for_status()


def adguard_get_clients(s: requests.Session, arguments) -> dict[str, dict]:
    """
    GET Request to retrieve all clients from Adguard. They are then organized
    in a dictionary where the mac-address is a key. If they do not have a
    mac-address, they are ignored. TODO: Should they be?
    :param s:   requests.Session
    :param arguments: argparse arguments
    :return:    dict[str, dict] -> {mac_addr: client-obj}
    """
    r = s.get("{}/control/clients".format(arguments.adguard_url))
    r.raise_for_status()
    clients = dict()
    if r.json()['clients'] is not None:
        for client in r.json()['clients']:
            mac = None
            for item in client['ids']:
                if len(item) == 17:
                    mac = item
            if mac is not None:
                clients[mac] = client
    return clients


def adguard_add_client(s: requests.Session, client, adguard_url):
    """
    POST request to create a NEW client. A Unifi OS client object/dict
    is required.
    :param adguard_url: base-url for adguard
    :param s:       requests.Session
    :param client:  unifi-os client-dict
    :return:        None
    """
    if client.get("name") is None:
        print("[sync] Client {} needs to be named.".format(client["display_name"]))
    else:
        print("[sync] Adding client {} to AdGuard".format(client["display_name"]))
        ip = client.get('fixed_ip') or client.get('ip')
        if not ip or not client.get('mac'):
            print(f"Skipping {client.get('display_name', 'unknown')} due to missing IP or MAC")
            return

        data = {
            "name": client['name'],
            "ids": [
                ip,
                client['mac']
            ],
            "use_global_settings": True,
            # "filtering_enabled": True,
            # "parental_enabled": True,
            # "safebrowsing_enabled": True,
            # "safe_search": {
            #    "enabled": True,
            #    "bing": True,
            #    "duckduckgo": True,
            #    "ecosia": True,
            #    "google": True,
            #    "pixabay": True,
            #    "yandex": True,
            #    "youtube": True
            # },
            "use_global_blocked_services": True,
            "tags": [],
        }
        r = s.post("{}/control/clients/add".format(adguard_url), json=data)
        r.raise_for_status()


def adguard_delete_all(s: requests.Session, clients: list[str], adguard_url):
    """
    Used to clean up clients in AdGuard. Since AdGuard clients are merely names for existing
    entities, deleting all doesn't remove any data. It just deletes the relationship between
    IP-ADDR and a Name.
    :param s:       requests.Session
    :param clients: list of client names
    :param adguard_url: base-url for adguard
    :return:        None
    """
    for c in clients:
        r = s.post("{}/control/clients/delete".format(adguard_url), json={"name": c})
        r.raise_for_status()


def adguard_update_client(s: requests.Session, client, old_name, adguard_url):
    """
    POST request to update a client. This request will update the name and
    IDS (mac_addr, ip_addr) of the client object in AdGuard.
    :param s:           requests.Session
    :param client:      unifi-os client-dict
    :param old_name:    the original name (from AdGuard client-dict)
    :param adguard_url: base-url for adguard
    :return:            None
    """
    print("[sync] Updating client {} in AdGuard".format(old_name))
    ip = client.get('fixed_ip') or client.get('ip')
    data = {
        "name": old_name,
        "data": {
            "upstreams": [],
            "tags": [],
            "name": client['name'],
            "blocked_services": None,
            "ids": [
                ip,
                client['mac']
            ],
            "filtering_enabled": False,
            "parental_enabled": False,
            "safebrowsing_enabled": False,
            "safesearch_enabled": False,
            "use_global_blocked_services": True,
            "use_global_settings": True
        }
    }
    r = s.post("{}/control/clients/update".format(adguard_url), json=data)
    r.raise_for_status()


def main():
    args = parse_args()
    start_ts = datetime.now(tz=timezone.utc)
    print(f"[sync] Start cycle at {start_ts}")
    # create session
    session = requests.Session()

    # login to unifi and retrieve clients
    unifi_login(session, args)
    print("[sync] Retrieving active clients from Unifi...")
    unifi_clients = unifi_get_active_clients(session, args)

    # login to adguard and retrieve clients
    adguard_login(session, args)
    print("[sync] Retrieving clients from AdGuard...")
    adguard_clients = adguard_get_clients(session, args)

    # determine changes
    print("[sync] Calculating changes...")
    unifi_active_client_macs = set(list(unifi_clients.keys()))
    adguard_client_macs = set(list(adguard_clients.keys()))
    new_clients = unifi_active_client_macs - adguard_client_macs
    existing_clients = unifi_active_client_macs.intersection(adguard_client_macs)
    modified_clients = 0

    # make changes if necessary
    if len(new_clients) > 0:
        for c in new_clients:
            adguard_add_client(session, unifi_clients[c], args.adguard_url)
    if len(existing_clients) > 0:
        for c in existing_clients:
            ip = unifi_clients[c].get('fixed_ip') or unifi_clients[c].get('ip')
            unifi_data = {ip, unifi_clients[c]['mac']}
            if (unifi_data != set(adguard_clients[c]['ids'])) or unifi_clients[c]['name'] != adguard_clients[c]['name']:
                modified_clients += 1
                print(f"[sync] Differences found for client {unifi_clients[c]['name']}, updating...")
                adguard_update_client(session, unifi_clients[c], adguard_clients[c]['name'], args.adguard_url)
                adguard_update_client(session, unifi_clients[c], adguard_clients[c]['name'], args.adguard_url)
    if len(new_clients) == 0 and modified_clients == 0:
        print("[sync] No changes required.")
    else:
        print("[sync] Changes made: {} added, {} modified.".format(len(new_clients), modified_clients))
    end_ts = datetime.now(tz=timezone.utc)
    print(f"[sync] End cycle at {end_ts}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # avoid crashing container; log and continue
        print(f"[sync] Sync failed: {e}")
