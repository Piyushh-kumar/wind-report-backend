import os
import resend
# ... (keep your existing import statements and PDF generation code)

# Set your Resend API key (you can sign up free at resend.com)
resend.api_key = "re_YourActualApiKeyHere"

def process_wind_assessment(email: str, location_str: str):
    # 1. Parse coordinates and fetch weather data (existing logic)
    try:
        lat_lon = [float(x.strip()) for x in location_str.split(',')]
        lat, lon = lat_lon[0], lat_lon[1]
    except Exception:
        lat, lon = 28.6139, 77.2090

    api_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=wind_speed_10m"
    try:
        response = requests.get(api_url)
        data = response.json()
        baseline_speed = data.get("current", {}).get("wind_speed_10m", 3.2)
        baseline_speed_ms = round(baseline_speed / 3.6, 2)
    except Exception:
        baseline_speed_ms = 3.5

    # 2. Hellman Power Law calculation
    alpha = 0.14
    heights = [10, 25, 50, 100]
    wind_profile = {}
    for z in heights:
        v_z = baseline_speed_ms * ((z / 10.0) ** alpha)
        wind_profile[z] = round(v_z, 2)

    mean_speed_50m = wind_profile[50]
    if mean_speed_50m >= 3.5:
        vawt_status = "SUITABLE: The average wind velocity profile satisfies baseline torque activation criteria for Damless VAWT grids."
    else:
        vawt_status = "MARGINAL: Low average velocity profiles detected. Supplementary micro-wind channel orientation advised."

    # 3. Generate PDF
    pdf_path = generate_wind_pdf(email, location_str, wind_profile, vawt_status)

    # 4. Email the PDF report to the user
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        params = {
            "from": "Maini Renewables <onboarding@resend.dev>",
            "to": [email],
            "subject": "Your Wind Assessment & VAWT Suitability Report",
            "html": "<p>Hello,</p><p>Thank you for requesting a wind site assessment with Maini Renewables. Please find your detailed multi-height wind velocity and VAWT suitability report attached.</p><p>Best regards,<br><strong>Maini Renewables Engineering Team</strong></p>",
            "attachments": [
                {
                    "filename": "wind_assessment_report.pdf",
                    "content": list(pdf_bytes)
                }
            ]
        }
        resend.Emails.send(params)
    except Exception as email_err:
        print(f"Failed to send email: {email_err}")

    return pdf_path