# AR.IO Gateway Deployment

Ansible deployment for AR.IO Gateway nodes.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd fluence-ar.io-deployment
   ```

2. **Create and activate venv**
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   uv sync
   ```

4. **Configure Fluence Cloud API**
   Create `fluence-vm.yml` with your API credentials:
   ```yaml
   api_key: "your-fluence-api-key"
   ssh_key_name: "your-ssh-public-key"
   ```

5. **Create VMs via Fluence Cloud**
   ```bash
   make create-vm VM_NAME=ar-io-node-1  # Creates VM and adds to inventory
   make create-vm VM_NAME=ar-io-node-2  # Create additional VMs as needed
   make list-vms                         # Verify VMs are created
   ```

6. **Configure vault**
   Create `group_vars/ar_io_nodes/vault.yml` with your wallet addresses
   ```yaml
   vault_ar_io_wallet: "your-arweave-wallet-address-43-characters-long"
   vault_observer_wallet: "observer-wallet-address-43-characters-long"
   ```

7. **Deploy AR.IO Gateway**
   ```bash
   make test          # Test connectivity to created VMs
   make deploy-ar-io  # Deploy the gateway to all VMs
   ```

8. **Test your gateway**
   ```bash
   curl -k --tlsv1.2 https://VM-IP/info
   ```

## Structure

- `playbooks/` - AR.IO deployment playbooks
- `inventory/` - Server inventories
- `group_vars/` - Group variables and vault files
- `roles/` - Reusable Ansible roles
- `secrets/` - Sensitive data (git-ignored)

## Management

```bash
make help           # Show available commands
make create-vm VM_NAME=ar-io-node-X # Create new VM
make delete-vm      # Delete VM (interactive selection)
make list-vms       # List all VMs
make test          # Test server connectivity
make deploy-ar-io [HOST=hostname]  # Deploy AR.IO gateway
make cleanup-ar-io [HOST=hostname] # Remove AR.IO installation
```

## Configuration

### Fluence Cloud API
Edit `fluence-vm.yml`:
- `api_key`: Your Fluence Cloud API key
- `ssh_key_name`: SSH key name registered in your Fluence account

### Vault Variables
Edit `group_vars/ar_io_nodes/vault.yml`:
- `vault_domain_name`: Your server IP or domain
- `vault_ar_io_wallet`: Your Arweave wallet address
- `vault_observer_wallet`: Observer wallet address (can be same as above)

### ARNS Setup (Optional)
If you have a domain with wildcard DNS setup:
1. Uncomment `ARNS_ROOT_HOST` in the deployed `.env` file
2. Set it to your domain name
3. Restart the containers

## Troubleshooting

- Gateway serves content directly without ARNS redirects by default
- Self-signed SSL certificates are generated automatically
- Check container logs: `sudo docker-compose logs -f` in `/opt/ar-io-node`
