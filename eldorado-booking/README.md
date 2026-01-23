# Eldorado Home Rentals - Booking Assistant v2

Hybrid booking form with AI-powered guest screening and email notifications.

## Features

- ✅ Clean booking form for guests
- ✅ AI-powered guest scoring (1-10)
- ✅ Risk detection and property matching
- ✅ Draft response generation
- ✅ **Email notifications** when new bookings arrive
- ✅ Working "Open in Email" button
- ✅ Working "Re-analyze" button

## Setup

### 1. Deploy to Streamlit Cloud

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/mikezhang23/eldorado-booking.git
git push -u origin main --force
```

### 2. Set Up EmailJS (Free - 200 emails/month)

1. Go to [emailjs.com](https://www.emailjs.com/) and create free account
2. **Add Email Service:**
   - Dashboard → Email Services → Add New Service
   - Choose Gmail (or your provider)
   - Connect your eldoradohomerentals@gmail.com
   - Note your **Service ID** (e.g., `service_abc123`)

3. **Create Email Template:**
   - Dashboard → Email Templates → Create New Template
   - Use this template:

```
Subject: 🏠 New Booking Request: {{guest_name}} - {{nights}} nights

New booking request received!

GUEST DETAILS:
Name: {{guest_name}}
Email: {{guest_email}}
Phone: {{guest_phone}}

BOOKING DETAILS:
Property: {{property}}
Check-in: {{check_in}}
Check-out: {{check_out}}
Duration: {{nights}} nights
Guests: {{guests}}
Type: {{booking_type}}

MESSAGE:
{{message}}

{{score_info}}

---
Submitted: {{submitted_at}}
View in dashboard: https://eldorado-booking.streamlit.app/?host=true
```

   - Set "To Email" to: `{{to_email}}`
   - Note your **Template ID** (e.g., `template_xyz789`)

4. **Get Public Key:**
   - Dashboard → Account → API Keys
   - Copy your **Public Key**

### 3. Add Secrets to Streamlit Cloud

Go to your app → Settings → Secrets, add:

```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
EMAILJS_SERVICE_ID = "service_abc123"
EMAILJS_TEMPLATE_ID = "template_xyz789"
EMAILJS_PUBLIC_KEY = "your_public_key"
```

### 4. Embed on Squarespace

Replace your booking form with:

```html
<div style="width:100%;max-width:800px;margin:0 auto;">
  <iframe 
    src="https://eldorado-booking.streamlit.app/?embedded=true"
    style="width:100%;height:950px;border:none;border-radius:12px;box-shadow:0 4px 20px rgba(0,0,0,0.08);"
    title="Booking Request Form"
  ></iframe>
</div>
```

## URLs

- **Guest form:** `https://eldorado-booking.streamlit.app/`
- **Host dashboard:** `https://eldorado-booking.streamlit.app/?host=true`

## How Email Notifications Work

When a guest submits the form:
1. Form data is processed
2. AI analyzes the guest (score, signals, draft response)
3. Email is sent to eldoradohomerentals@gmail.com with:
   - Guest details
   - Booking info
   - AI score and assessment
   - Link to host dashboard
4. Guest sees confirmation
5. You review in email or dashboard and respond

## Troubleshooting

**Email not sending?**
- Check EmailJS dashboard for errors
- Verify all 3 secrets are set correctly
- Make sure Gmail is connected in EmailJS

**"Open in Email" not working?**
- This opens your default email client (Mail, Outlook, etc.)
- On mobile, it should open the mail app
- If nothing happens, your browser may be blocking mailto: links
