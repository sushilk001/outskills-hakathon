# 🚀 Deployment Guide

**Production-ready deployment instructions for Multi-Agent DevOps Incident Analysis Suite**

---

## 📋 Prerequisites

- Docker and Docker Compose installed
- API keys (OpenAI or OpenRouter)
- (Optional) Slack and JIRA credentials for integrations

---

## 🐳 Docker Deployment (Recommended)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Hackathon
   ```

2. **Create environment file:**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Build and run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Open browser: `http://localhost:8501`

### Manual Docker Build

```bash
# Build the image
docker build -t devops-incident-suite:latest .

# Run the container
docker run -d \
  -p 8501:8501 \
  --env-file .env \
  --name devops-incident-suite \
  devops-incident-suite:latest
```

---

## ☁️ Cloud Deployment

### Streamlit Cloud

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repository
4. Add environment variables in settings
5. Deploy!

### AWS/Azure/GCP

Use the Dockerfile with your preferred container service:
- AWS ECS/Fargate
- Azure Container Instances
- Google Cloud Run

---

## 🔧 Environment Variables

Required:
- `OPENAI_API_KEY` or `OPENROUTER_API_KEY`
- `USE_OPENROUTER` (true/false)

Optional:
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID`
- `JIRA_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`

---

## 📊 Health Checks

The Docker container includes a health check endpoint:
- Health URL: `http://localhost:8501/_stcore/health`
- Check status: `docker ps` (look for "healthy" status)

---

## 🔒 Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use secrets management** in production (AWS Secrets Manager, Azure Key Vault, etc.)
3. **Limit API key permissions** - Use least privilege principle
4. **Enable HTTPS** - Use reverse proxy (nginx, Traefik) in production
5. **Regular updates** - Keep dependencies updated

---

## 📈 Scaling

### Horizontal Scaling

Use Docker Compose with multiple replicas:
```yaml
services:
  app:
    deploy:
      replicas: 3
```

### Resource Limits

Set in `docker-compose.yml`:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## 🐛 Troubleshooting

### Container won't start
- Check logs: `docker-compose logs app`
- Verify environment variables
- Check port availability

### API errors
- Verify API keys are correct
- Check rate limits
- Review API quotas

### Performance issues
- Increase container resources
- Enable caching
- Optimize vector store size

---

## 📝 Maintenance

### Update Application
```bash
git pull
docker-compose build
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f app
```

### Backup Data
```bash
# Backup cookbooks and vector stores
docker cp devops-incident-suite:/app/cookbooks ./backup/cookbooks
docker cp devops-incident-suite:/app/vector_stores ./backup/vector_stores
```

---

## ✅ Production Checklist

- [ ] Environment variables configured
- [ ] API keys secured (not in code)
- [ ] HTTPS enabled (reverse proxy)
- [ ] Health checks configured
- [ ] Logging enabled
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Security scan completed
- [ ] Performance tested
- [ ] Documentation updated

---

## 👤 Project Creator

**Created by:** Sushil Kumar  
🔗 [LinkedIn](https://www.linkedin.com/in/sushilk001/)

