## PolicyKit (pkexec) single-prompt setup

ClamApp uses `pkexec` for privileged UFW actions. By default, you may be prompted frequently.

To make authorization **persist for the session**, you can install a PolicyKit rule that uses
`auth_admin_keep`.

### Recommended (safe) approach

1. Create a restricted helper script at `/usr/local/bin/clamapp-ufw-helper` that **whitelists**
   only the UFW operations ClamApp needs.
2. Install the PolicyKit action file from `docs/policykit/clamapp-ufw.policy` to:
   `/usr/share/polkit-1/actions/clamapp-ufw.policy`
3. Ensure the helper is executable:

```bash
sudo install -m 0755 /usr/local/bin/clamapp-ufw-helper /usr/local/bin/clamapp-ufw-helper
sudo install -m 0644 docs/policykit/clamapp-ufw.policy /usr/share/polkit-1/actions/clamapp-ufw.policy
```

4. Restart your session (or restart `polkit` if applicable), then run ClamApp again.

### Notes

- **Do not** whitelist arbitrary commands.
- The helper should validate argv strictly and always call `/usr/sbin/ufw` (absolute path).

