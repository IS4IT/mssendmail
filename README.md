# mssendmail

**Microsoft Graph-based sendmail replacement with a persistent queue for Linux**

mssendmail provides a drop-in sendmail interface for sending emails via the Microsoft Graph API.
It stores emails in a local queue and processes them asynchronously via systemd-managed background worker.

## Features

- Drop-in compatible with basic sendmail calls (e.g. for Mastodon)
- Persistent queue (handles temporary outages)
- Sends via Microsoft Entra ID + Graph API
- Environment-based config via /etc/mssendmail/.env
- File-based logging

## Prerequisites

1. An Shared Mailbox in Exchange Online
1. An App Registration
2. A Client Secret
3. Assign API Permissions
    * Add Mail.Send as application permission
4. Restrict App Access to specific Mailboxes
    New-ApplicationAccessPolicy -AppId "<client-id>" -PolicyScopeGroupId "<mail-enabled group>" -AccessRight RestrictAccess

## Installation
- Install uv
- Clone this repo
    - uv pip install .
    - Registers the commands mssendmail and mssendmail-worker
- Create user mssendmail
    sudo useradd --system --home /var/lib/mssendmail --shell /usr/sbin/nologin mssendmail
- Create folder
    sudo mkdir -p /var/lib/mssendmail/queue /var/log/mssendmail /etc/mssendmail
    sudo chown -R mssendmail:mssendmail /var/lib/mssendmail /var/log/mssendmail
    sudo chmod 750 /var/lib/mssendmail /var/log/mssendmail
    sudo touch /etc/mssendmail/.env
    sudo chown root:mssendmail /etc/mssendmail/.env
    sudo chmod 640 /etc/mssendmail/.env
- Configure
- Create a user 
- Create required directories
- Add the systemd service for the mssendmail-worker
    - cp util/mssendmail-queue-worker.service /etc/systemd/system
    - systemctl daemon-reexec
    - systemctl enable --now mssendmail-queue-worker.service

## Configuration

File: /etc/mssendmail/.env

TENANT_ID=your-tenant-id
CLIENT_ID=your-app-client-id
CLIENT_SECRET=your-app-secret
SENDER=noreply@yourdomain.com

QUEUE_DIR=/var/lib/mssendmail/queue
LOG_DIR=/var/log/mssendmail

## Manual Usage
Queue a mail:
cat mail.eml | mssendmail

Manually process queue:
mssendmail-worker

### In the uv
cat mail > uv run mssendmail/queue_writer.py


## Missing features

- Retry mechanism is missing backoff
- Logrotation
- Packaging
