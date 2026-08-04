"""
deployment-namespace.py - Look up which namespace a k8s Deployment lives in.

Purpose:
    Given a Deployment name, queries the cluster for every Deployment across
    all namespaces and prints the namespace of the first match. Useful when
    you know a workload's name but not where it's deployed.

Requires:
    kubectl on PATH, configured against the target cluster (not bundled in
    this image). Uses only the Python standard library otherwise.

Usage:
    python ~/scripts/deployment-namespace.py <deployment-name>
"""

import argparse
import json
import subprocess


def get_namespace(name):
    cmd = ["kubectl", "get", "-A", "deployment", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        _json = json.loads(result.stdout)
        for deployment in _json["items"]:
            if name == deployment["metadata"]["name"]:
                namespace = deployment["metadata"]["namespace"]
                return namespace
    else:
        print("Error:", result.stderr.decode())
        return None
    print("Error: Deployment not found")
    return None


parser = argparse.ArgumentParser(description="Get namespace for a deployment")
parser.add_argument("name", type=str, help="Name of the deployment")
args = parser.parse_args()

namespace = get_namespace(args.name)
if namespace:
    print(namespace)
