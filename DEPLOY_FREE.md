# Resume Parser - Free Deployment Guide

## 🚀 Best Free Options (2026)

### Option 1: Render.com (⭐ RECOMMENDED)
**Pros**: Easy deployment, free tier solid, good performance
**Cost**: Free tier includes up to 500 hours/month + 0.5GB RAM

#### Deploy to Render:

1. **Push to GitHub** (Render pulls from Git)
```bash
git init
git add .
git commit -m "Production ready resume parser"
git remote add origin https://github.com/YOUR_USERNAME/resume-parser.git
git push -u origin main
```

2. **Create Render account** at https://render.com

3. **Create Web Service**:
   - Connect GitHub repo
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn --bind 0.0.0.0:$PORT --workers 2 app:app`
   - Environment: Add `FLASK_ENV=production`

4. **Deploy** - Takes ~2-3 minutes

✅ Your app available at: `https://resume-parser-xxxxx.onrender.com`

---

### Option 2: Railway.app
**Pros**: Very easy, nice dashboard
**Cost**: Free tier $5/month credits

1. **Push to GitHub**
2. Go to railway.app
3. Click "New Project" → "Deploy from GitHub"
4. Select repo
5. Auto-detects `Procfile` and deploys

---

### Option 3: Heroku (Classic - Still Works)
**Pros**: Industry standard
**Cost**: Free tier removed but cheapest paid $5/month

Not recommended anymore (removed free tier), but still option.

---

### Option 4: PythonAnywhere
**Pros**: Python-focused, easy
**Cost**: Free tier available

1. Go to pythonanywhere.com
2. Upload files via web interface
3. Configure WSGI file
4. Enable app

---

### Option 5: Replit
**Pros**: Instant deployment, built-in IDE
**Cost**: Free tier available

1. Go to replit.com
2. Create new Replit from GitHub
3. Set `.env` variables
4. Deploy (Replit handles it)

---

## 📋 Recommended: Render.com Setup (Step-by-Step)

### Step 1: Prepare GitHub

```bash
# Initialize git (if not done)
git init

# Add all files
git add .

# Commit
git commit -m "Resume Parser - Production Ready"

# Create GitHub repo (https://github.com/new)
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/resume-parser.git
git branch -M main
git push -u origin main
```

### Step 2: Create Render Account
- Visit https://render.com
- Sign up with GitHub
- Authorize repo access

### Step 3: Deploy Web Service
1. Click "New +" → "Web Service"
2. Select your `resume-parser` repository
3. Configure:
   - **Name**: `resume-parser`
   - **Region**: Choose closest to users
   - **Branch**: `main`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`

4. **Environment Variables**:
   ```
   FLASK_ENV=production
   ```

5. Click "Deploy Web Service"

### Step 4: Watch Deployment
- Render shows real-time build logs
- Takes ~2-3 minutes first time
- You get a `.onrender.com` URL when done

### Step 5: Test
```bash
curl https://your-app.onrender.com/
# Should return HTML UI
```

---

## ⚠️ Important: Cold Starts

Free tier apps go to sleep after 15 min inactivity.

**Fix**: Use uptime monitoring:
```bash
# Visit UptimeRobot.com
# Create monitor for https://your-app.onrender.com
# Checks every 5 minutes = keeps app alive
```

---

## 💾 File Storage Limitation

Free tier has **ephemeral storage** (deletes on restart).

**Solution 1**: Upload to S3 (Amazon free tier)
**Solution 2**: Use Render's persistent disk ($7/month)
**Solution 3**: Store in MongoDB Atlas (free tier)

For MVP, just use ephemeral (files clear on restart - that's OK).

---

## 🔐 Environment Variables on Render

Set sensitive vars in Render dashboard:
1. Service Settings → Environment
2. Add each var:
   - `FLASK_ENV`: `production`
   - `ADMIN_TOKEN`: Generate secure token
   - `MASTER_KEY`: Optional (Fernet key)

They're injected at runtime - never committed to Git.

---

## 📊 Performance Expectations

**Free Tier Performance:**
- Response time: 500ms - 2s first hit (cold start)
- Concurrent users: ~5-10
- Parsing speed: Same as local
- Uptime: 99.5%

**For production use**, upgrade to paid:
- Render Pro: $12/month for better performance
- Railway: $10/month
- Dedicated: $50+/month

---

## 🚀 Deploy Right Now (5 Minutes)

```bash
# 1. Initialize Git
git init && git add . && git commit -m "init"

# 2. Create GitHub repo (web UI)
# https://github.com/new → Create repository

# 3. Push code
git remote add origin https://github.com/YOUR_USERNAME/resume-parser.git
git branch -M main && git push -u origin main

# 4. Go to render.com
# Connect GitHub → New Web Service → Configure & Deploy

# 5. Done! Your URL: https://resume-parser-xxxxx.onrender.com
```

---

## 🆘 Troubleshooting

| Issue | Fix |
|-------|-----|
| **502 Bad Gateway** | Check build/start logs, ensure Procfile correct |
| **Import Error** | Add package to requirements.txt, redeploy |
| **Slow first load** | Normal - cold start. Use uptimerobot.com to keep warm |
| **"Disk full"** | Free tier ephemeral. Upgrade or reduce file storage |
| **ENV vars not working** | Set in Render dashboard, not .env file |

---

## 📈 Upgrade When Needed

**When to upgrade from free:**
- > 100 concurrent users
- > 1000 requests/day
- Need persistent storage
- Need custom domain

**Pricing:**
- Render: $12/month → 2GB RAM, persistent disk
- Railway: $10/month → Similar features
- Heroku: $25+/month if you still use it

---

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] requirements.txt has all packages
- [ ] Procfile created with correct start command
- [ ] Environment variables set in Render dashboard
- [ ] FLASK_ENV set to production
- [ ] App deployed and running
- [ ] Test URL accessible
- [ ] Uptimerobot configured (keep warm)

---

## 🎉 You're Live!

Once deployed, you have:
- ✅ Public URL for your Resume Parser
- ✅ Automatic HTTPS/SSL
- ✅ Free domain (or use custom domain later)
- ✅ Scalable (upgrade when needed)
- ✅ Auto-redeploys on Git push

Share your URL: `https://your-resume-parser-xxx.onrender.com`

---

**Total cost**: $0 initially, can upgrade later
**Setup time**: ~15 minutes
**Ready to use**: Immediately after deployment
