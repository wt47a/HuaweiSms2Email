# Huawei SMS to Home Assistant Email Forwarder

This AppDaemon module monitors a Huawei LTE router for new SMS messages and forwards them to a designated Home Assistant notification service (Email).

## Purpose & Environment

- **Context:** Specifically designed for users with Huawei LTE routers (e.g., B535, B818) who need to receive 2FA codes, system alerts, or standard SMS via email.
- **Environment:** Runs as a Python script within AppDaemon.
- **Integration:** Communicates with Home Assistant (tested on HA Core Docker) and utilizes the `huawei-lte-api`.
- **Key Features:**
  - Batch processing (pagination)
  - Automatic "mark as read" on the router
  - Network proxy support
- **Tested on:**
  - Devices: E3372h-320, H135-380
  - Home assistant: Home Assistant Container / Core 2025.12.3
  - AppDaemon v4.5.13
  - Python libs: huawei-lte-api-1.11.0

---

# Setup Requirements

## Architecture

- **Home Assistant:** Tested on Home Assistant Core (Docker)
- **AppDaemon:** Version 4.x
- **Hardware:** Huawei LTE router compatible with `huawei-lte-api`

## Connectivity

- AppDaemon must have network access to the Huawei router (direct or via proxy)
- AppDaemon must have access to the Home Assistant API
> Important: Internet access during container startup is not required if the modules were already installed manually or via the Docker Compose method above.

## Parameters

Collect the following before deployment:
- Huawei Router:
  - IP address
  - Admin username
  - Password
- Home Assistant:
  - Long-Lived Access Token (generated from the HA user profile)
- Notifier Name:
  - Name of the notification service created earlier (e.g. `notifier_smtp_sms_gateway`)

---

# Installation Instructions

## 1. Home Assistant Email Gateway Configuration

Before setting up the script, you must have a notification service defined in your `configuration.yaml`. This service will be the destination for your SMS messages.

### Example SMTP configuration in Home Assistant

```yaml
notify:
  - name: "notifier_smtp_sms_gateway"
    platform: smtp
    server: "mail.yourserver.com"
    port: 587
    timeout: 15
    sender: "hass@yourdomain.com"
    encryption: starttls
    username: "hass@yourdomain.com"
    password: "your_email_password"
    recipient:
      - "yourname@domain.com"
    sender_name: "Huawei SMS Gateway"
```

For detailed SMTP setup, refer to the Home Assistant SMTP Integration documentation.

## AppDaemon Configuration (`apps.yaml`)

AppDeamon must be setup before running scripts. Chos one of the following configuration methods proposed or adopt your instalation to your purpose, then setup worker module.

### AppDaemon Setup

> The module requires `huawei-lte-api` and `requests`. These must be installed in the environment where AppDaemon is running.
Choose **ONE** of the following methods depending on your setup:

#### Method A: Docker Compose (Recommended)

Modify your `docker-compose.yml` to install dependencies before starting the AppDaemon service:
```yaml
services:
  appdaemon:
    container_name: appdaemon
    image: acouch/appdaemon:latest
    command: >
      bash -c "pip3 install huawei-lte-api requests && appdaemon"
    volumes:
      - ./config:/conf
```

#### Method B: Standalone AppDaemon (Manual Installation)

If AppDaemon runs directly on the host OS:
```bash
pip install huawei-lte-api requests
```

#### Method C: Pure Docker (via requirements.txt)

Create a `requirements.txt` file in the AppDaemon `/config` folder:
```text
huawei-lte-api
requests
```
> Note: AppDaemon will attempt to install these from the internet on every startup.

### Module Setup (`apps.yaml`)

Add the following block to `apps.yaml`:

```yaml
sms_forwarder:
  module: sms_to_ha_email
  class: SmsToHaEmail
  base_address: "192.168.8.1"
  username: "admin"
  password: "YourRouterPassword"
  interval: 60
  batch_size: 5
  notifier_name: "notifier_smtp_sms_gateway"
  # proxy_url: "http://192.168.1.50:8888"
  title_template: "[SMS] From: {sender}"
  body_template: |
    Date: {date}
    From: {sender}
    Message: {content}
```

#### Configuration Parameters

| Parameter | Description | Default |
|---|---|---|
| `base_address` | IP address of the Huawei router | Required |
| `notifier_name` | Name of the HA notify service | Required |
| `interval` | Seconds between SMS inbox checks | `300` |
| `batch_size` | Number of messages processed per page | `5` |
| `proxy_url` | HTTP/HTTPS proxy for restricted networks | `None` |

---

### Logging & Debug

Logs are available via the AppDaemon console or log files.

### Log Levels

- `INFO`
  - General status
  - Successful forwarding
- `DEBUG`
  - Detailed message counts
  - Synchronization information
- `ERROR`
  - Communication failures
  - Delivery failures

### Follow logs in Docker

```bash
docker logs -f appdaemon
```

---

## Credits & References

This project relies on the excellent [huawei-lte-api](https://github.com/Salamek/huawei-lte-api) library by [Salamek](https://github.com/Salamek).

---

**Keywords:** `home-assistant`, `appdaemon`, `huawei-lte`, `sms-forwarder`, `python`, `self-hosted`, `automation`, `2fa-notifications`

---
Use at your own risk. Frequent polling may affect router responsiveness.
