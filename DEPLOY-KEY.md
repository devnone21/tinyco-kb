# Deploy key setup (run on LXC host)

The GitHub Actions deploy workflow uses SSH. Run this once on the LXC to
generate a dedicated key, install the public half, and print the private
half for the GitHub secret.

## Steps

```bash
# 1. Run the helper
bash scripts/setup-lxc-deploy-key.sh

# 2. In GitHub repo → Settings → Secrets and variables → Actions:
#    LXC_SSH_KEY   = the printed private key block (including BEGIN/END)
#    LXC_SSH_HOST  = tony@10.1.1.X  (or root@<hostname>)
#    LXC_SSH_PORT  = 22

# 3. Push to main → workflow runs → site deploys
```

## Optional variables (not secrets, in repo Settings → Variables)

| Variable | Default | Purpose |
|---|---|---|
| `PUBLIC_SITE_URL` | `https://kb.example.com` | Public URL used by sitemap + smoke test |

## Security notes

- The key has **no passphrase** because GitHub Actions doesn't support
  interactive passphrase entry. Mitigation: the key is dedicated to this
  one repo, has `command=` restrictions available (set in `authorized_keys`
  if you want to be extra-paranoid), and the secret is repo-scoped.
- For maximum hardening, restrict the key in `~/.ssh/authorized_keys`:
  ```
  command="/opt/kb-site/scripts/authorized-commands.sh",no-port-forwarding,
  no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAA... kb-ci-deploy
  ```
  And implement the allowed-command wrapper (git pull, docker compose, etc.).
