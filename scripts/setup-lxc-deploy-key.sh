# LXC deploy key setup for the KB site CI
#
# Run on the LXC `docker` host, as the user that owns /opt/kb-site
# (typically `root`, or a `tony` user in the `docker` group).

# 1. Create a dedicated CI key (no passphrase — safe for CI use only)
ssh-keygen -t ed25519 -C "kb-ci-deploy" -f ~/.ssh/kb_ci_ed25519 -N ""

# 2. Allow this key to log in
echo "$(cat ~/.ssh/kb_ci_ed25519.pub)" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# 3. Make sure the deploying user can run docker without sudo
sudo usermod -aG docker "${USER:-root}"
# (log out & back in if you're not root)

# 4. Print the private key to copy into GitHub → Settings → Secrets → LXC_SSH_KEY
echo
echo "============================================================"
echo "Copy the block below into GitHub secret LXC_SSH_KEY:"
echo "============================================================"
cat ~/.ssh/kb_ci_ed25519
echo "============================================================"
echo
echo "Then set:"
echo "  LXC_SSH_HOST = $(whoami)@<this-host-ip-or-name>"
echo "  LXC_SSH_PORT = 22"
