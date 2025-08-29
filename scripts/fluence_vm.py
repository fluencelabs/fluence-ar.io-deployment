#!/usr/bin/env python3
"""
Fluence VM Management Script
Simple wrapper for Fluence Cloud API to create, list, and delete VMs
"""

import os
import sys
import json
import time
import requests
import yaml
from typing import Dict, List, Optional


class FluenceVM:
    def __init__(self, config_path: str = "fluence-vm.yml"):
        self.config = self._load_config(config_path)
        self.api_key = self.config["api_key"]
        self.ssh_key_name = self.config["ssh_key_name"]
        self.base_url = "https://api.fluence.dev/vms/v3"
        self.inventory_path = "inventory/production/hosts"
        self.vault_path = "group_vars/ar_io_nodes/vault.yml"
        
    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Config file {config_path} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"Error parsing config file: {e}")
            sys.exit(1)
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _get_headers_simple(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def create_vm(self, vm_name: str) -> bool:
        """Create VM and wait for it to become Active"""
        payload = {
            "constraints": {
                "additionalResources": {
                    "storage": [
                        {
                            "supply": 1975,
                            "type": "NVMe",
                            "units": "GiB"
                        }
                    ]
                },
                "basicConfiguration": "cpu-16-ram-32gb-storage-25gb",
                "datacenter": {
                    "countries": ["BE"]
                }
            },
            "instances": 1,
            "vmConfiguration": {
                "hostname": vm_name,
                "name": vm_name,
                "openPorts": [
                    {"port": 80, "protocol": "tcp"},
                    {"port": 80, "protocol": "udp"},
                    {"port": 443, "protocol": "tcp"},
                    {"port": 443, "protocol": "udp"},
                    {"port": 3000, "protocol": "tcp"},
                    {"port": 3000, "protocol": "udp"}
                ],
                "osImage": "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img",
                "sshKeys": [self.ssh_key_name]
            }
        }
        
        try:
            response = requests.post(self.base_url, 
                                   headers=self._get_headers(), 
                                   json=payload)
            
            if response.status_code != 201:
                print(f"Failed to create VM: {response.status_code} - {response.text}")
                return False
                
            result = response.json()
            if not result or len(result) == 0:
                print("No VM data in response")
                return False
                
            vm_id = result[0]["vmId"]
            print(f"VM creation initiated: {vm_name} (ID: {vm_id})")
            
            # Poll for VM status
            if self._wait_for_vm_active(vm_id, vm_name):
                return True
            else:
                print(f"VM {vm_name} failed to become active")
                return False
                
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return False
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Invalid response format: {e}")
            return False
    
    def _wait_for_vm_active(self, vm_id: str, vm_name: str) -> bool:
        """Poll VM status until Active or timeout"""
        max_wait = 600  # 10 minutes
        interval = 10   # 10 seconds
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                status_url = f"{self.base_url}/status?ids={vm_id}"
                response = requests.get(status_url, headers=self._get_headers_simple())
                
                if response.status_code != 200:
                    print(f"Status check failed: {response.status_code}")
                    time.sleep(interval)
                    elapsed += interval
                    continue
                
                result = response.json()
                if not result or len(result) == 0:
                    print("No status data in response")
                    time.sleep(interval)
                    elapsed += interval
                    continue
                
                status = result[0]["status"]
                print(f"VM {vm_name} status: {status}")
                
                if status == "Active":
                    public_ip = result[0]["publicIp"]
                    print(f"VM {vm_name} is active with IP: {public_ip}")
                    self._add_to_inventory(vm_name, public_ip)
                    return True
                elif status == "Failed":
                    print(f"VM {vm_name} failed to launch")
                    return False
                
                time.sleep(interval)
                elapsed += interval
                
            except requests.RequestException as e:
                print(f"Status check request failed: {e}")
                time.sleep(interval)
                elapsed += interval
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"Invalid status response: {e}")
                time.sleep(interval)
                elapsed += interval
        
        print(f"Timeout waiting for VM {vm_name} to become active")
        return False
    
    def _add_to_inventory(self, vm_name: str, ip: str):
        """Add VM to Ansible inventory"""
        try:
            os.makedirs(os.path.dirname(self.inventory_path), exist_ok=True)
            
            # Read existing inventory
            inventory_lines = []
            if os.path.exists(self.inventory_path):
                with open(self.inventory_path, 'r') as f:
                    inventory_lines = f.readlines()
            
            # Add VM entry
            vm_entry = f"{vm_name} ansible_host={ip} ansible_user=ubuntu\n"
            
            # Find [ar_io_nodes] section and add entry
            in_ar_io_section = False
            inserted = False
            
            for i, line in enumerate(inventory_lines):
                if line.strip() == "[ar_io_nodes]":
                    in_ar_io_section = True
                elif line.startswith("[") and in_ar_io_section:
                    # Insert before next section
                    inventory_lines.insert(i, vm_entry)
                    inserted = True
                    break
            
            if not inserted:
                # Append to end or create new inventory
                if not inventory_lines or not any("[ar_io_nodes]" in line for line in inventory_lines):
                    inventory_lines.extend([
                        "[ar_io_nodes]\n",
                        vm_entry,
                        "\n[all:vars]\n",
                        "ansible_python_interpreter=/usr/bin/python3\n"
                    ])
                else:
                    inventory_lines.append(vm_entry)
            
            with open(self.inventory_path, 'w') as f:
                f.writelines(inventory_lines)
                
            print(f"Added {vm_name} to inventory")
            
            # Also update vault.yml
            self._add_to_vault(vm_name, ip)
            
        except IOError as e:
            print(f"Failed to update inventory: {e}")
    
    def _add_to_vault(self, vm_name: str, ip: str):
        """Add VM to vault domain names mapping"""
        try:
            os.makedirs(os.path.dirname(self.vault_path), exist_ok=True)
            
            # Read existing vault
            vault_data = {}
            if os.path.exists(self.vault_path):
                with open(self.vault_path, 'r') as f:
                    vault_data = yaml.safe_load(f) or {}
            
            # Ensure vault_domain_names exists and is a dict
            if 'vault_domain_names' not in vault_data or vault_data['vault_domain_names'] is None:
                vault_data['vault_domain_names'] = {}
            
            # Add VM to domain names mapping
            vault_data['vault_domain_names'][vm_name] = ip
            
            # Write back to vault
            with open(self.vault_path, 'w') as f:
                yaml.dump(vault_data, f, default_flow_style=False)
            
            print(f"Added {vm_name} to vault.yml")
            
        except (IOError, yaml.YAMLError) as e:
            print(f"Failed to update vault.yml: {e}")
    
    def list_vms(self) -> List[Dict]:
        """Get list of Active and Launching VMs"""
        try:
            url = f"{self.base_url}?page=1&per_page=50"
            response = requests.get(url, headers=self._get_headers_simple())
            
            if response.status_code != 200:
                print(f"Failed to list VMs: {response.status_code}")
                return []
            
            all_vms = response.json()
            # Filter for Active and Launching VMs only
            filtered_vms = [vm for vm in all_vms if vm.get('status') in ['Active', 'Launching']]
            return filtered_vms
            
        except requests.RequestException as e:
            print(f"Failed to list VMs: {e}")
            return []
    
    def delete_vm(self):
        """Interactive VM deletion"""
        vms = self.list_vms()
        if not vms:
            print("No VMs found")
            return
        
        print("Available VMs:")
        for i, vm in enumerate(vms):
            print(f"{i+1}. {vm['vmName']} ({vm['id']}) - {vm['status']}")
        
        try:
            choice = int(input("Select VM to delete (number): ")) - 1
            if choice < 0 or choice >= len(vms):
                print("Invalid selection")
                return
            
            selected_vm = vms[choice]
            vm_id = selected_vm['id']
            vm_name = selected_vm['vmName']
            
            confirm = input(f"Delete VM {vm_name}? (y/N): ")
            if confirm.lower() != 'y':
                print("Cancelled")
                return
            
            # Delete VM
            payload = {"vmIds": [vm_id]}
            response = requests.delete(self.base_url, 
                                     headers=self._get_headers(), 
                                     json=payload)
            
            if response.status_code == 200:
                print(f"VM {vm_name} deleted successfully")
                self._remove_from_inventory(vm_name)
            else:
                print(f"Failed to delete VM: {response.status_code}")
                
        except ValueError:
            print("Invalid input")
        except requests.RequestException as e:
            print(f"Delete request failed: {e}")
    
    def _remove_from_inventory(self, vm_name: str):
        """Remove VM from inventory"""
        try:
            if not os.path.exists(self.inventory_path):
                return
                
            with open(self.inventory_path, 'r') as f:
                lines = f.readlines()
            
            # Remove line containing vm_name
            filtered_lines = [line for line in lines if not line.startswith(vm_name)]
            
            with open(self.inventory_path, 'w') as f:
                f.writelines(filtered_lines)
            
            print(f"Removed {vm_name} from inventory")
            
            # Also remove from vault.yml
            self._remove_from_vault(vm_name)
            
        except IOError as e:
            print(f"Failed to update inventory: {e}")
    
    def _remove_from_vault(self, vm_name: str):
        """Remove VM from vault domain names mapping"""
        try:
            if not os.path.exists(self.vault_path):
                return
                
            with open(self.vault_path, 'r') as f:
                vault_data = yaml.safe_load(f) or {}
            
            # Remove VM from domain names mapping
            if 'vault_domain_names' in vault_data and vm_name in vault_data['vault_domain_names']:
                del vault_data['vault_domain_names'][vm_name]
                
                # Write back to vault
                with open(self.vault_path, 'w') as f:
                    yaml.dump(vault_data, f, default_flow_style=False)
                
                print(f"Removed {vm_name} from vault.yml")
            
        except (IOError, yaml.YAMLError) as e:
            print(f"Failed to update vault.yml: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python fluence_vm.py <create|delete|list> [vm_name]")
        sys.exit(1)
    
    command = sys.argv[1]
    fluence = FluenceVM()
    
    if command == "create":
        if len(sys.argv) < 3:
            print("VM name required for create command")
            sys.exit(1)
        vm_name = sys.argv[2]
        success = fluence.create_vm(vm_name)
        sys.exit(0 if success else 1)
        
    elif command == "delete":
        fluence.delete_vm()
        
    elif command == "list":
        vms = fluence.list_vms()
        if vms:
            for vm in vms:
                ip = vm.get('publicIp', 'No IP')
                print(f"{vm['vmName']} - {vm['status']} - {ip}")
        else:
            print("No VMs found")
    else:
        print("Unknown command. Use: create, delete, or list")


if __name__ == "__main__":
    main()