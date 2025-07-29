# AR.IO Gateway Deployment

Ansible deployment for AR.IO Gateway nodes.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd ansible-deployments
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

4. **Configure inventory**
   Edit `inventory/production/hosts` with your servers

5. **Configure vault**
   Edit `group_vars/ar_io_nodes/vault.yml` with your domain and wallet addresses

6. **Deploy AR.IO Gateway**
   ```bash
   make test          # Test connectivity
   make deploy-ar-io  # Deploy the gateway
   ```

7. **Test your gateway**
   ```bash
   curl -k --tlsv1.2 https://YOUR-SERVER-IP/info
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
make test          # Test server connectivity
make deploy-ar-io  # Deploy AR.IO gateway
make cleanup-ar-io # Remove AR.IO installation
```

## Configuration

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