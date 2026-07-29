import os
import base64
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_wind_pdf(email: str, location: str, wind_data: dict, vawt_status: str, filename="wind_assessment_report.pdf"):
    doc = SimpleDocTemplate(filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#0F172A'), spaceAfter=6)
    subtitle_style = ParagraphStyle('SubTitleStyle', parent=styles['Normal'], fontSize=12, textColor=colors.HexColor('#64748B'), spaceAfter=20)
    heading_style = ParagraphStyle('HeadingStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#0F172A'), spaceAfter=10, spaceBefore=15)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#334155'), spaceAfter=8)

    story.append(Paragraph("Maini Renewables — Site Assessment Report", title_style))
    story.append(Paragraph(f"Generated for Location: {location} | Target Recipient: {email}", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Multi-Height Wind Velocity Profiles", heading_style))
    story.append(Paragraph("Using meteorological baseline records and Hellman Power Law shear adjustments, projected average wind speeds across varied vertical heights are outlined below:", body_style))

    table_data = [["Height Level", "Projected Mean Wind Speed", "Suitability Status"]]
    for height, speed in wind_data.items():
        status = "Viable for VAWT" if speed >= 3.5 else "Low Kinetic Energy"
        table_data.append([f"{height} Meters", f"{speed} m/s", status])

    t = Table(table_data, colWidths=[120, 180, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#334155')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))

    story.append(Paragraph("2. Vertical Axis Wind Turbine (VAWT) Suitability Analysis", heading_style))
    story.append(Paragraph(f"<b>Assessment Result:</b> {vawt_status}", body_style))
    story.append(Paragraph("Vertical-axis configurations excel in turbulent micro-climates and low-speed zones. Based on the local spatial coordinates provided, the structural deployment profile matches operational parameters.", body_style))
    
    doc.build(story)
    return filename

def process_wind_assessment(email: str, location_str: str):
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

    pdf_path = generate_wind_pdf(email, location_str, wind_profile, vawt_status)

    # Automatically send the generated PDF to the user's email inbox via Resend REST API
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        api_key = os.environ.get("RESEND_API_KEY", "")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "from": "Maini Renewables <onboarding@resend.dev>",
            "to": [email],
            "subject": "Your Wind Assessment & VAWT Suitability Report",
            "html": "<p>Hello,</p><p>Thank you for requesting a wind site assessment with Maini Renewables. Please find your detailed multi-height wind velocity and VAWT suitability report attached.</p><p>Best regards,<br><strong>Maini Renewables Engineering Team</strong></p>",
            "attachments": [
                {
                    "filename": "wind_assessment_report.pdf",
                    "content": pdf_base64
                }
            ]
        }

        res = requests.post("https://api.resend.com/emails", json=payload, headers=headers)
        if res.status_code != 200:
            print(f"Resend API Error: {res.text}")
        else:
            print("Email successfully dispatched via Resend API.")

    except Exception as email_err:
        print(f"Failed to send email: {email_err}")

    return pdf_path