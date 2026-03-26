# ClamApp UFW PolicyKit Installation

## Overview
This document describes how to install the PolicyKit policy file that enables ClamApp to manage UFW firewall with single-session authentication.

## Files
- `com.clamapp.policy` - PolicyKit policy file for UFW execution

## Installation Commands

### Install the PolicyKit policy file:
```bash
sudo cp com.clamapp.policy /usr/share/polkit-1/actions/
sudo chmod 644 /usr/share/polkit-1/actions/com.clamapp.policy
```

### Verify installation:
```bash
ls -la /usr/share/polkit-1/actions/com.clamapp.policy
```

## What This Policy Does
- Allows ClamApp to execute `/usr/sbin/ufw` via `pkexec`
- Uses `auth_admin_keep` so users only authenticate ONCE per session
- Provides GUI-friendly authentication dialogs
- Ensures secure privilege escalation for firewall management

## Benefits
- **Single Authentication**: Password prompt only once per desktop session
- **Professional UX**: No repetitive password dialogs during firewall operations
- **Secure**: PolicyKit ensures proper authorization before privilege escalation
- **Persistent**: Authentication remains valid for the entire session

## Testing
After installation, launch ClamApp and try any firewall operation. You should see:
1. A single password prompt when first accessing firewall features
2. No additional prompts for subsequent firewall operations in the same session
3. Professional "Unlock" button if authentication is cancelled

## Troubleshooting
If the policy doesn't work:
1. Verify the file exists in `/usr/share/polkit-1/actions/`
2. Check permissions: `ls -la /usr/share/polkit-1/actions/com.clamapp.policy`
3. Restart your desktop session
4. Ensure PolicyKit service is running: `systemctl --user status polkit-agent`

## Security Note
This policy only allows execution of `/usr/sbin/ufw` and requires administrator authentication. It does not grant unrestricted root access.
