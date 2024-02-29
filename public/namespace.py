import subprocess
import json
import argparse

def get_namespace(name):
    # Run kubectl command to get the namespace for the deployment
    cmd = ["kubectl", "get", "-A", "deployment", "-o", "json"]
    result = subprocess.run(cmd, capture_output=True)
    
    # Parse the JSON output to extract the namespace
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
    
    
# Parse command line arguments
parser = argparse.ArgumentParser(description='Get namespace for a deployment')
parser.add_argument('name', type=str, help='Name of the deployment')
args = parser.parse_args()
        
# Example usage
# deployment_name = "minecraft"
namespace = get_namespace(args.name)
if namespace:
    print(namespace)

