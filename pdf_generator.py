import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def gutschein_pdf_erstellen(code: str, wert: float, empfaenger: str, absender: str, widmung: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()

    # QR-Code generieren
    qr_img = qrcode.make(code)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1e293b'), alignment=1, spaceAfter=20)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=12, leading=16, textColor=colors.HexColor('#334155'))
    italic_style = ParagraphStyle('ItalicStyle', parent=body_style, fontName='Helvetica-Oblique', fontSize=14, leading=18, alignment=1)

    story.append(Paragraph("Hotel am blauen Wunder", title_style))
    story.append(Paragraph("<b>WERTGUTSCHEIN</b>", ParagraphStyle('Sub', parent=title_style, fontSize=16, textColor=colors.HexColor('#0284c7'))))
    story.append(Spacer(1, 20))

    story.append(Paragraph(f"<b>Gutscheinwert:</b> {wert:.2f} €", ParagraphStyle('Wert', parent=body_style, fontSize=18, textColor=colors.HexColor('#0f172a'))))
    story.append(Spacer(1, 15))

    if empfaenger:
        story.append(Paragraph(f"<b>Für:</b> {empfaenger}", body_style))
    if absender:
        story.append(Paragraph(f"<b>Von:</b> {absender}", body_style))
    
    story.append(Spacer(1, 15))

    if widmung:
        story.append(Paragraph(f"„{widmung}“", italic_style))
        story.append(Spacer(1, 20))

    # QR Code & Details Tabelle
    qr_image = Image(qr_buffer, width=120, height=120)
    code_text = Paragraph(f"<b>Gutscheincode:</b><br/><font size=14 color='#0284c7'><b>{code}</b></font><br/><br/><font size=9 color='#64748b'>Einlösbar an der Rezeption und im Restaurant.</font>", body_style)

    table_data = [[code_text, qr_image]]
    t = Table(table_data, colWidths=[350, 130])
    t.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
    ]))
    
    story.append(t)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
