# CI/CD Setup with Forgejo and Woodpecker CI

This document explains how to set up continuous integration and deployment for the Meshtastic MQTT Bot using Forgejo (self-hosted Git) and Woodpecker CI.

## Architecture

```mermaid
flowchart LR
    Dev[Developer] -->|git push| Forgejo[Forgejo Git Server]
    Forgejo -->|webhook| Woodpecker[Woodpecker CI]
    
    subgraph "Woodpecker Pipeline"
        Test[Run Tests]
        Build[Build Frontend]
        Docker[Build Docker Image]
        Deploy[Deploy to Pi]
        
        Test --> Build
        Build --> Docker
        Docker --> Deploy
    end
    
    Woodpecker --> RaspberryPi[Raspberry Pi]
    
    classDef devStyle fill:#4ade80,stroke:#16a34a,stroke-width:2px
    classDef infraStyle fill:#60a5fa,stroke:#2563eb,stroke-width:2px
    classDef deployStyle fill:#f472b6,stroke:#db2777,stroke-width:2px
    
    class Dev devStyle
    class Forgejo,Woodpecker,Test,Build,Docker,Deploy infraStyle
    class RaspberryPi deployStyle
```

## Prerequisites

### On Your LAN
- **Forgejo** server running at `http://192.168.8.191:3000`
- **Woodpecker CI** server (can be installed alongside Forgejo)
- **Raspberry Pi** with Docker and Docker Compose installed

### Repository Setup
1. Repository created in Forgejo: `http://192.168.8.191:3000/mac/baymesh-mqtt-bot`
2. Git remote configured:
   ```bash
   git remote add forgejo ssh://git@192.168.8.191:22/mac/baymesh-mqtt-bot.git
   ```

## Woodpecker CI Installation

### Using Docker Compose on the Same Server as Forgejo

```yaml
# woodpecker-docker-compose.yml
version: '3'

services:
  woodpecker-server:
    image: woodpeckerci/woodpecker-server:latest
    ports:
      - 8000:8000
      - 9000:9000
    volumes:
      - woodpecker-server-data:/var/lib/woodpecker/
    environment:
      - WOODPECKER_OPEN=true
      - WOODPECKER_HOST=http://192.168.8.191:8000
      - WOODPECKER_FORGEJO=true
      - WOODPECKER_FORGEJO_URL=http://192.168.8.191:3000
      - WOODPECKER_FORGEJO_CLIENT=<your-forgejo-oauth-client-id>
      - WOODPECKER_FORGEJO_SECRET=<your-forgejo-oauth-secret>
      - WOODPECKER_AGENT_SECRET=<generate-random-secret>
      - WOODPECKER_ADMIN=mac

  woodpecker-agent:
    image: woodpeckerci/woodpecker-agent:latest
    depends_on:
      - woodpecker-server
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - WOODPECKER_SERVER=woodpecker-server:9000
      - WOODPECKER_AGENT_SECRET=<same-secret-as-above>

volumes:
  woodpecker-server-data:
```

### Generate Secrets
```bash
# Generate agent secret
openssl rand -hex 32

# Store in docker-compose.yml or use .env file
```

### Create OAuth Application in Forgejo

1. Go to Forgejo → Settings → Applications → OAuth2 Applications
2. Click "Create a new OAuth2 Application"
3. **Application Name**: Woodpecker CI
4. **Redirect URI**: `http://192.168.8.191:8000/authorize`
5. Copy the **Client ID** and **Client Secret**
6. Update `woodpecker-docker-compose.yml` with these values

### Start Woodpecker CI
```bash
docker compose -f woodpecker-docker-compose.yml up -d
```

## Pipeline Configuration

The project includes three pipeline files:

### 1. Main Pipeline (`.woodpecker.yml`)
Runs on every push to master/main:
- Runs tests with coverage
- Builds frontend
- Builds Docker image
- Deploys to Raspberry Pi
- Sends notifications on failure

### 2. Test Pipeline (`.woodpecker/test.yml`)
Runs on every push and PR:
- Installs dependencies
- Runs pytest
- Generates coverage report

### 3. Deploy Pipeline (`.woodpecker/deploy.yml`)
Runs only on push to master/main:
- Builds production frontend
- Creates Docker image
- Deploys to Raspberry Pi via SSH
- Verifies deployment with health check
- Rolls back on failure

## Setting Up Secrets in Woodpecker

Secrets are used to store sensitive information like SSH keys and hostnames.

### Via Woodpecker UI
1. Go to your repository in Woodpecker
2. Click **Settings** → **Secrets**
3. Add the following secrets:

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `pi_host` | Raspberry Pi hostname or IP | `192.168.8.100` |
| `pi_user` | SSH username on Pi | `pi` |
| `pi_ssh_key` | Private SSH key for Pi access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `slack_webhook` | (Optional) Slack webhook URL for notifications | `https://hooks.slack.com/...` |

### Via Woodpecker CLI
```bash
# Install woodpecker CLI
brew install woodpecker-ci/tap/woodpecker-cli

# Configure
woodpecker-cli login http://192.168.8.191:8000

# Add secrets
woodpecker-cli secret add \
  --repository mac/baymesh-mqtt-bot \
  --name pi_host \
  --value "192.168.8.100"

woodpecker-cli secret add \
  --repository mac/baymesh-mqtt-bot \
  --name pi_user \
  --value "pi"

# For SSH key (multiline)
cat ~/.ssh/id_rsa | woodpecker-cli secret add \
  --repository mac/baymesh-mqtt-bot \
  --name pi_ssh_key \
  --value @-
```

## Raspberry Pi Setup

### 1. Install Docker and Docker Compose
```bash
# Update packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin

# Verify
docker --version
docker compose version
```

### 2. Create Deployment Directory
```bash
# Create directory
sudo mkdir -p /opt/meshtastic-mqtt-bot
sudo chown $USER:$USER /opt/meshtastic-mqtt-bot
cd /opt/meshtastic-mqtt-bot

# Clone repository
git clone ssh://git@192.168.8.191:22/mac/baymesh-mqtt-bot.git .

# Create .env file
cp .env.example .env
nano .env  # Fill in your values
```

### 3. Set Up SSH Access for Woodpecker
```bash
# On your development machine, generate SSH key if you don't have one
ssh-keygen -t ed25519 -C "woodpecker-ci"

# Copy public key to Raspberry Pi
ssh-copy-id pi@192.168.8.100

# Test connection
ssh pi@192.168.8.100 "docker ps"
```

### 4. Configure Firewall (Optional)
```bash
# Allow API port
sudo ufw allow 8000/tcp comment "Meshtastic MQTT Bot API"

# Enable firewall
sudo ufw enable
```

## Enabling the Repository in Woodpecker

1. Log in to Woodpecker UI: `http://192.168.8.191:8000`
2. Click **Repositories** → **Activate**
3. Find `mac/baymesh-mqtt-bot`
4. Click **Activate**
5. Configure webhook in Forgejo (should auto-configure)

## Testing the Pipeline

### Manual Trigger
1. Make a small change to the code
2. Commit and push:
   ```bash
   git add .
   git commit -m "test: trigger CI pipeline"
   git push forgejo master
   ```
3. Watch the pipeline in Woodpecker UI

### Expected Flow
```
1. Code pushed to Forgejo
   ↓
2. Webhook triggers Woodpecker
   ↓
3. Woodpecker pulls code
   ↓
4. Run tests (pytest)
   ↓ (if pass)
5. Build frontend (npm run build)
   ↓
6. Build Docker image
   ↓
7. SSH to Raspberry Pi
   ↓
8. Pull latest code
   ↓
9. Run docker compose down
   ↓
10. Run docker compose up -d
   ↓
11. Verify health endpoint
   ↓
12. ✅ Deployment complete
```

## Monitoring Deployments

### View Pipeline Status
```bash
# Via Woodpecker CLI
woodpecker-cli pipeline list mac/baymesh-mqtt-bot

# View specific pipeline
woodpecker-cli pipeline info mac/baymesh-mqtt-bot 42

# View logs
woodpecker-cli pipeline logs mac/baymesh-mqtt-bot 42
```

### Check Raspberry Pi Status
```bash
# SSH to Pi
ssh pi@192.168.8.100

# Check running containers
docker compose ps

# View logs
docker compose logs -f --tail=100

# Check health
curl http://localhost:8000/health
```

## Troubleshooting

### Pipeline Fails at Test Step
```bash
# Run tests locally
pytest -v

# Check dependencies
pip install -r requirements.txt
```

### Deployment Fails - SSH Connection
```bash
# Test SSH from Woodpecker server
docker exec -it woodpecker-agent ssh pi@192.168.8.100

# Check SSH key is added to Pi
cat ~/.ssh/authorized_keys
```

### Deployment Fails - Docker Build
```bash
# SSH to Pi and build manually
ssh pi@192.168.8.100
cd /opt/meshtastic-mqtt-bot
docker compose build --no-cache
docker compose up -d
```

### Health Check Fails
```bash
# Check if API is running
curl -v http://192.168.8.100:8000/health

# Check logs for errors
docker compose logs meshtastic-stats-bot
```

## Advanced Configuration

### Matrix Builds (Multiple Python Versions)
```yaml
# .woodpecker/test-matrix.yml
matrix:
  PYTHON_VERSION:
    - 3.11
    - 3.12

steps:
  - name: test
    image: python:${PYTHON_VERSION}
    commands:
      - pip install -r requirements.txt
      - pytest
```

### Caching Dependencies
```yaml
steps:
  - name: restore-cache
    image: meltwater/drone-cache:latest
    settings:
      restore: true
      cache_key: "pip-{{ checksum 'requirements.txt' }}"
      backend: "filesystem"
      mount: [".venv"]

  - name: install
    image: python:3.11
    commands:
      - pip install -r requirements.txt

  - name: save-cache
    image: meltwater/drone-cache:latest
    settings:
      rebuild: true
      cache_key: "pip-{{ checksum 'requirements.txt' }}"
      backend: "filesystem"
      mount: [".venv"]
```

### Blue-Green Deployment
```yaml
steps:
  - name: deploy-green
    image: appleboy/drone-ssh
    settings:
      script:
        - docker compose -f docker-compose.green.yml up -d
        - sleep 10
        - curl -f http://localhost:8001/health
        - docker compose -f docker-compose.blue.yml down
        - # Swap blue <-> green in nginx config
```

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Use SSH keys** instead of passwords
3. **Limit SSH key access** to specific commands if possible
4. **Enable webhook secrets** in Forgejo
5. **Use HTTPS** for Forgejo and Woodpecker in production
6. **Regular updates** of Docker images and dependencies
7. **Monitor pipeline logs** for suspicious activity

## Resources

- [Woodpecker CI Documentation](https://woodpecker-ci.org/docs/intro)
- [Forgejo Documentation](https://forgejo.org/docs/latest/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Project README](../README.md)
- [Architecture Documentation](ARCHITECTURE.md)

