"""
Eldorado Home Rentals - Booking Request Assistant
Hybrid: Customer-facing form + AI-powered screening for host
With email notifications via EmailJS
"""

import streamlit as st
import anthropic
import json
from datetime import datetime, date, timedelta
import urllib.parse
import requests

# Page config
st.set_page_config(
    page_title="Book Now | Eldorado Home Rentals",
    page_icon="🏠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Check for URL parameters
query_params = st.query_params

# Custom CSS matching Eldorado brand
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    .main-header {
        font-family: 'Playfair Display', serif;
        font-size: 2.2rem;
        font-weight: 600;
        text-align: center;
        margin-bottom: 0.5rem;
        color: #1a1a1a;
    }
    .sub-header {
        font-family: 'Inter', sans-serif;
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    .stButton > button {
        background-color: #1a1a1a;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #333;
        transform: translateY(-1px);
    }
    .success-box {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        margin: 2rem 0;
    }
    .info-card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .host-section {
        background-color: #fff8e6;
        border: 1px solid #ffe0b2;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 2rem;
    }
    .score-high { background-color: #d4edda; color: #155724; padding: 1rem; border-radius: 8px; }
    .score-medium { background-color: #fff3cd; color: #856404; padding: 1rem; border-radius: 8px; }
    .score-low { background-color: #f8d7da; color: #721c24; padding: 1rem; border-radius: 8px; }
    
    /* Hide sidebar in embedded mode */
    section[data-testid="stSidebar"] {
        display: none;
    }
    
    /* Fix button styling */
    .action-button {
        display: inline-block;
        background-color: #1a1a1a;
        color: white !important;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        margin: 5px;
        text-align: center;
    }
    .action-button:hover {
        background-color: #333;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Get secrets with proper error handling
def get_secret(key, default=""):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return default

# Get all secrets at startup
ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY", "")
EMAILJS_SERVICE_ID = get_secret("EMAILJS_SERVICE_ID", "")
EMAILJS_TEMPLATE_ID = get_secret("EMAILJS_TEMPLATE_ID", "")
EMAILJS_PUBLIC_KEY = get_secret("EMAILJS_PUBLIC_KEY", "")

def send_email_notification(form_data, analysis=None):
    """Send email notification using EmailJS"""
    
    # Check if EmailJS is configured
    if not all([EMAILJS_SERVICE_ID, EMAILJS_TEMPLATE_ID, EMAILJS_PUBLIC_KEY]):
        return False, f"EmailJS not configured. Service: {bool(EMAILJS_SERVICE_ID)}, Template: {bool(EMAILJS_TEMPLATE_ID)}, Key: {bool(EMAILJS_PUBLIC_KEY)}"
    
    try:
        # Prepare email content
        score_info = ""
        if analysis and "error" not in analysis:
            score = analysis["qualification"]["score"]
            priority = analysis["qualification"]["priority"]
            score_info = f"\n\n🎯 AI ANALYSIS:\nScore: {score}/10 ({priority.upper()})\n{analysis['qualification']['score_reasoning']}\n\nRecommended Property: {analysis['property_match']['best_fit']}"
        
        template_params = {
            "to_email": "eldoradohomerentals@gmail.com",
            "from_name": form_data["name"],
            "guest_name": form_data["name"],
            "guest_email": form_data["email"],
            "guest_phone": form_data.get("phone", "Not provided"),
            "property": form_data["property"],
            "check_in": form_data["check_in"],
            "check_out": form_data["check_out"],
            "nights": str(form_data["nights"]),
            "guests": str(form_data["guests"]),
            "booking_type": form_data["booking_type"],
            "message": form_data.get("message", "None") or "None",
            "score_info": score_info,
            "submitted_at": form_data["submitted_at"]
        }
        
        # Send via EmailJS REST API
        response = requests.post(
            "https://api.emailjs.com/api/v1.0/email/send",
            json={
                "service_id": EMAILJS_SERVICE_ID,
                "template_id": EMAILJS_TEMPLATE_ID,
                "user_id": EMAILJS_PUBLIC_KEY,
                "template_params": template_params
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "Email sent"
        else:
            return False, f"EmailJS error ({response.status_code}): {response.text}"
            
    except requests.exceptions.Timeout:
        return False, "Email request timed out"
    except Exception as e:
        return False, f"Email exception: {str(e)}"

def analyze_guest(form_data):
    """Run AI analysis on the booking request"""
    if not ANTHROPIC_API_KEY:
        return {"error": "Anthropic API key not configured"}
    
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        inquiry_text = f"""
Guest Name: {form_data['name']}
Email: {form_data['email']}
Phone: {form_data.get('phone', 'N/A')}
Company: {form_data.get('company', 'N/A')}
Property Interest: {form_data['property']}
Check-in: {form_data['check_in']}
Check-out: {form_data['check_out']}
Duration: {form_data['nights']} nights
Number of Guests: {form_data['guests']}
Booking Type: {form_data['booking_type']}
Additional Message: {form_data.get('message', 'None provided')}
"""
        
        system_prompt = """You are a guest screening assistant for Eldorado Home Rentals, a premium mid-term rental company in Las Vegas with three properties:

1. **Eldorado Ln** - Single story resort-style home with pool, beautiful white kitchen, expansive backyard. Best for families and photo shoots.
2. **Katie Ave** - Modern smart home with stunning private backyard. Best for professionals and small groups.
3. **Runestone St** - Japanese wabi-sabi style with mountain views. Best for creatives, couples, and influencers.

Analyze this booking request and respond with valid JSON only:

{
    "qualification": {
        "score": number 1-10,
        "priority": "high|medium|low",
        "score_reasoning": "1-2 sentence explanation"
    },
    "guest_profile": {
        "guest_type": "string",
        "positive_signals": ["list"],
        "risk_signals": ["list"]
    },
    "property_match": {
        "best_fit": "Eldorado Ln|Katie Ave|Runestone St",
        "match_reasoning": "why this property fits"
    },
    "pricing_suggestion": {
        "rate_tier": "standard|premium|discount",
        "reasoning": "brief explanation"
    },
    "response_strategy": {
        "respond_within": "1 hour|same day|24 hours",
        "tone": "string",
        "key_points": ["what to address in response"]
    },
    "draft_response": "A warm, professional 2-paragraph response to the guest"
}

Scoring: 9-10 (long stays, corporate, photo shoots), 7-8 (2+ weeks, professionals), 5-6 (1 week, families), 3-4 (weekends, large groups), 1-2 (party red flags)"""

        message_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Analyze this booking request:\n\n{inquiry_text}"}]
        )
        
        response_text = message_response.content[0].text
        
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        return json.loads(response_text.strip())
        
    except Exception as e:
        return {"error": str(e)}

# Initialize session state
if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'form_data' not in st.session_state:
    st.session_state.form_data = None
if 'email_sent' not in st.session_state:
    st.session_state.email_sent = False
if 'email_error' not in st.session_state:
    st.session_state.email_error = ""

# Check if host mode
is_host_mode = query_params.get("host", "false").lower() == "true"

# Header
st.markdown('<p class="main-header">🏠 Request a Booking</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Fill out the form below and we\'ll get back to you within 24 hours</p>', unsafe_allow_html=True)

# FORM VIEW
if not st.session_state.submitted:
    
    with st.form("booking_form"):
        st.subheader("📋 Your Information")
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name *", placeholder="John Smith")
        with col2:
            email = st.text_input("Email Address *", placeholder="john@email.com")
        
        col3, col4 = st.columns(2)
        with col3:
            phone = st.text_input("Phone Number", placeholder="(555) 123-4567")
        with col4:
            company = st.text_input("Company (if applicable)", placeholder="Company name")
        
        st.subheader("🏡 Booking Details")
        
        property_choice = st.selectbox(
            "Which property are you interested in? *",
            [
                "Not sure yet - help me choose",
                "Eldorado Ln - Resort-style with pool",
                "Katie Ave - Modern smart home",
                "Runestone St - Japanese wabi-sabi style"
            ]
        )
        
        col5, col6 = st.columns(2)
        with col5:
            check_in = st.date_input(
                "Check-in Date *",
                min_value=date.today(),
                value=date.today() + timedelta(days=7)
            )
        with col6:
            check_out = st.date_input(
                "Check-out Date *",
                min_value=date.today() + timedelta(days=1),
                value=date.today() + timedelta(days=14)
            )
        
        col7, col8 = st.columns(2)
        with col7:
            guests = st.number_input("Number of Guests *", min_value=1, max_value=16, value=2)
        with col8:
            booking_type = st.selectbox(
                "Booking Type *",
                [
                    "Vacation / Leisure",
                    "Business / Work Trip",
                    "Relocation / Extended Stay",
                    "Photo / Video Shoot",
                    "Event / Gathering",
                    "Other"
                ]
            )
        
        st.subheader("💬 Tell Us More")
        
        message = st.text_area(
            "Additional details about your stay",
            placeholder="Tell us about your trip! What brings you to Las Vegas? Any special requests or questions?",
            height=120
        )
        
        agree = st.checkbox("I agree to be contacted about my booking request")
        
        submitted = st.form_submit_button("Submit Booking Request", type="primary")
        
        if submitted:
            if not name or not email:
                st.error("Please fill out all required fields (Name and Email)")
            elif not agree:
                st.error("Please agree to be contacted about your booking request")
            elif check_out <= check_in:
                st.error("Check-out date must be after check-in date")
            else:
                nights = (check_out - check_in).days
                st.session_state.form_data = {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "company": company,
                    "property": property_choice,
                    "check_in": str(check_in),
                    "check_out": str(check_out),
                    "nights": nights,
                    "guests": guests,
                    "booking_type": booking_type,
                    "message": message,
                    "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Run AI analysis
                if ANTHROPIC_API_KEY:
                    with st.spinner("Processing your request..."):
                        st.session_state.analysis_result = analyze_guest(st.session_state.form_data)
                
                # Send email notification
                email_success, email_msg = send_email_notification(
                    st.session_state.form_data, 
                    st.session_state.analysis_result
                )
                st.session_state.email_sent = email_success
                st.session_state.email_error = email_msg
                
                st.session_state.submitted = True
                st.rerun()

# CONFIRMATION VIEW
else:
    form_data = st.session_state.form_data
    analysis = st.session_state.analysis_result
    
    # Guest confirmation
    st.markdown("""
    <div class="success-box">
        <h2 style="margin:0;color:#155724;">✓ Request Received!</h2>
        <p style="margin:1rem 0 0 0;color:#155724;">Thank you for your booking request. We'll review your information and get back to you within 24 hours.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("📋 Your Request Summary")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {form_data['name']}")
        st.write(f"**Email:** {form_data['email']}")
        st.write(f"**Phone:** {form_data['phone'] or 'Not provided'}")
    with col2:
        st.write(f"**Property:** {form_data['property']}")
        st.write(f"**Dates:** {form_data['check_in']} → {form_data['check_out']} ({form_data['nights']} nights)")
        st.write(f"**Guests:** {form_data['guests']} | **Type:** {form_data['booking_type']}")
    
    if form_data.get('message'):
        st.write(f"**Message:** {form_data['message']}")
    
    st.markdown("---")
    st.markdown("Questions? Email us at **eldoradohomerentals@gmail.com**")
    
    # New request button
    if st.button("Submit Another Request", key="new_request"):
        st.session_state.submitted = False
        st.session_state.analysis_result = None
        st.session_state.form_data = None
        st.session_state.email_sent = False
        st.session_state.email_error = ""
        st.rerun()
    
    # HOST DASHBOARD
    if is_host_mode or ANTHROPIC_API_KEY:
        st.markdown("---")
        st.markdown("### 🔒 Host Dashboard")
        
        # Email notification status with detailed error
        if st.session_state.email_sent:
            st.success("✓ Email notification sent to eldoradohomerentals@gmail.com")
        else:
            st.warning(f"⚠️ Email notification not sent: {st.session_state.email_error}")
        
        # Debug info for host
        if is_host_mode:
            with st.expander("🔧 Debug Info"):
                st.write(f"**Anthropic API Key:** {'✓ Configured' if ANTHROPIC_API_KEY else '✗ Missing'}")
                st.write(f"**EmailJS Service ID:** {'✓ ' + EMAILJS_SERVICE_ID[:10] + '...' if EMAILJS_SERVICE_ID else '✗ Missing'}")
                st.write(f"**EmailJS Template ID:** {'✓ ' + EMAILJS_TEMPLATE_ID if EMAILJS_TEMPLATE_ID else '✗ Missing'}")
                st.write(f"**EmailJS Public Key:** {'✓ ' + EMAILJS_PUBLIC_KEY[:10] + '...' if EMAILJS_PUBLIC_KEY else '✗ Missing'}")
        
        if analysis and "error" not in analysis:
            score = analysis["qualification"]["score"]
            priority = analysis["qualification"]["priority"]
            
            # Score display
            if score >= 7:
                score_class = "score-high"
            elif score >= 4:
                score_class = "score-medium"
            else:
                score_class = "score-low"
            
            st.markdown(f'<div class="{score_class}"><strong>Guest Score: {score}/10</strong> | Priority: {priority.upper()} | Respond: {analysis["response_strategy"]["respond_within"]}</div>', unsafe_allow_html=True)
            
            st.write(f"**Assessment:** {analysis['qualification']['score_reasoning']}")
            
            # Property match
            st.subheader("🏡 Property Recommendation")
            st.success(f"**{analysis['property_match']['best_fit']}** — {analysis['property_match']['match_reasoning']}")
            
            # Signals
            col_a, col_b = st.columns(2)
            with col_a:
                st.write("**✅ Positive Signals:**")
                for signal in analysis["guest_profile"]["positive_signals"]:
                    st.write(f"• {signal}")
                if not analysis["guest_profile"]["positive_signals"]:
                    st.write("• None identified")
            with col_b:
                st.write("**🚩 Risk Signals:**")
                for signal in analysis["guest_profile"]["risk_signals"]:
                    st.write(f"• {signal}")
                if not analysis["guest_profile"]["risk_signals"]:
                    st.write("• None identified")
            
            # Draft response
            st.subheader("✉️ Draft Response")
            st.info(f"**Suggested tone:** {analysis['response_strategy']['tone']}")
            
            draft = analysis["draft_response"]
            response_text = st.text_area("Edit and copy:", value=draft, height=150, key="draft_response")
            
            # Action buttons
            st.subheader("⚡ Quick Actions")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Create mailto link
                subject = urllib.parse.quote("Re: Your Eldorado Home Rentals Booking Request")
                body = urllib.parse.quote(response_text)
                mailto_link = f"mailto:{form_data['email']}?subject={subject}&body={body}"
                
                st.markdown(f'<a href="{mailto_link}" class="action-button" target="_blank">📧 Open in Email Client</a>', unsafe_allow_html=True)
            
            with col2:
                # Download JSON
                json_data = json.dumps({**form_data, "analysis": analysis}, indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"booking_{form_data['name'].replace(' ', '_')}_{form_data['check_in']}.json",
                    mime="application/json",
                    key="download_json"
                )
            
            # Re-analyze button
            st.markdown("---")
            if st.button("🔄 Re-analyze This Request", key="reanalyze"):
                with st.spinner("Re-analyzing..."):
                    st.session_state.analysis_result = analyze_guest(form_data)
                st.rerun()
        
        elif analysis and "error" in analysis:
            st.error(f"Analysis error: {analysis['error']}")
            if st.button("🔄 Retry Analysis", key="retry"):
                with st.spinner("Retrying..."):
                    st.session_state.analysis_result = analyze_guest(form_data)
                st.rerun()
        else:
            st.warning("AI analysis not available. Add ANTHROPIC_API_KEY to Streamlit secrets.")
            st.json(form_data)

# Footer
st.markdown("""
<div style="text-align:center;color:#999;font-size:0.8rem;margin-top:3rem;padding-bottom:1rem;">
    Eldorado Home Rentals | Las Vegas, NV | eldoradohomerentals@gmail.com
</div>
""", unsafe_allow_html=True)
