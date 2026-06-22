# Deploy to Proxmox LXC `docker`

> Target: LXC `docker` on `jasperlake`. HTTPS via existing CF Tunnel. Auth via Cloudflare Access.

## One-time setup (on the LXC host)

```bash
# 1. Clone the repo
cd /opt
sudo git clone <your-git-url> kb-site
cd kb-site

# 2. Allow scripts to write content/updates without rebuild
sudo chown -R 1000:1000 src/content  # or whichever uid runs the writer

# 3. Build & start
sudo docker compose up -d --build

# 4. (Optional) For git-push auto-deploy via GitHub Actions:
#    see DEPLOY-KEY.md
```

## CF Tunnel routing

Edit your `cloudflared` config (location depends on your existing setup)
to add the KB upstream. See [cf-tunnel-snippet.yml](cf-tunnel-snippet.yml).

Then add the DNS record in Cloudflare:
- Type: CNAME
- Name: `kb` (or whatever you chose)
- Target: `<your-tunnel-id>.cfargotunnel.com`
- Proxy: **Proxied** ✓

## Cloudflare Access policy

1. Cloudflare Zero Trust → **Access** → **Applications** → **Add** → **Self-hosted**
2. Application domain: `kb.example.com`
3. Identity providers: enable **GitHub** and **Google**
   - First time: CF shows OAuth setup wizard for each
4. Policy:
   - Name: `allow-listed-users`
   - Action: **Allow**
   - Include → **Emails** → your email (add more as needed)
5. Save

Visit `https://kb.example.com` — you'll be redirected to CF Access login.

## Auto-rebuild on content change

Two options:

**A. Cron-driven rebuild** (recommended for script-generated content):
```cron
# /etc/cron.d/kb-rebuild  (on the host)
*/15 * * * * root cd /opt/kb-site && ./rebuild.sh >> /var/log/kb-rebuild.log 2>&1
```
Then have your PVE-morning-brief script write `.md` files into
`/opt/kb-site/src/content/updates/` — within 15 min the site rebuilds.

**B. Git-push webhook** (recommended for manual edits):
- Push to remote from your dev machine
- CF Worker / Gitea webhook hits a small rebuild endpoint on the LXC
- (We can wire this later if you want)

## Backup

```bash
# Backing up content is enough — site is fully reproducible
tar czf kb-content-$(date +%F).tar.gz -C /opt/kb-site/src content
```

## Convert PVE brief JSON → update `.md`

```bash
# Test the converter with the sample
python3 scripts/pve_brief_to_md.py --sample

# Generate an update from a real audit JSON
python3 scripts/pve_brief_to_md.py /path/to/brief.json \
    --out /opt/kb-site/src/content/updates/ --prefix pve-
# next cron_rebuild.sh tick picks it up (≤5 min)
# or trigger immediately:
curl -X POST https://hook.example.com/rebuild \
  -H "X-Hub-Signature-256: sha256=$(printf %s '' | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')" \
  --data-binary ''
```
