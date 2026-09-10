import secrets
import stripe
from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from pdf_generator import gutschein_pdf_erstellen
from database import get_db, Kunde, Gutschein, code_generieren

app = FastAPI(title="Hotel Gutschein System")

# Session-Verwaltung für Rezeptions-Login
app.add_middleware(SessionMiddleware, secret_key="HOTEL_SUPER_SECRET_KEY_2026")

templates = Jinja2Templates(directory="templates")

# Admin / Rezeption Zugangsdaten
ADMIN_USER = "admin"
ADMIN_PASSWORD = "MeinSicheresPasswort2026!"

def check_admin_session(request: Request):
    if not request.session.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            headers={"Location": "/admin/login"}
        )
    return True

# --- PUBLIC ROUTES ---
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/shop", response_class=HTMLResponse)
def shop_page(request: Request):
    return templates.TemplateResponse(request=request, name="shop.html")

# --- LOGIN / LOGOUT ---
@app.get("/admin/login", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"Fehler": None})

@app.post("/admin/login", response_class=HTMLResponse)
@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, Benutzername: str = Form(...), Passwort: str = Form(...)):
    is_user = secrets.compare_digest(Benutzername.encode("utf8"), ADMIN_USER.encode("utf8"))
    is_pass = secrets.compare_digest(Passwort.encode("utf8"), ADMIN_PASSWORD.encode("utf8"))

    if is_user and is_pass:
        request.session["is_admin"] = True
        return RedirectResponse(url="/admin/dashboard", status_code=303)

    return templates.TemplateResponse(
        request=request, 
        name="login.html", 
        context={"Fehler": "Ungültige Zugangsdaten"}
    )

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

# --- REZEPTION / ADMIN BEREICH (GESCHÜTZT) ---
@app.get("/admin/dashboard", dependencies=[Depends(check_admin_session)])
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    kunden = db.query(Kunde).all()
    gutscheine = db.query(Gutschein).all()

    # KPIs berechnen
    gesamt_gutscheine = len(gutscheine)
    gesamt_wert = sum(g.original_wert for g in gutscheine)
    offener_wert = sum(g.rest_wert for g in gutscheine)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "kunden": kunden,
            "gutscheine": gutscheine,
            "gesamt_gutscheine": gesamt_gutscheine,
            "gesamt_wert": gesamt_wert,
            "offener_wert": offener_wert
        }
    )

@app.post("/admin/kunde/neu", dependencies=[Depends(check_admin_session)])
def kunde_anlegen(name: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    neuer_kunde = Kunde(name=name, email=email)
    db.add(neuer_kunde)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/gutschein/erstellen", dependencies=[Depends(check_admin_session)])
def gutschein_erstellen_vor_ort(
    wert: float = Form(...),
    empfaenger: str = Form(None),
    absender: str = Form(None),
    widmung: str = Form(None),
    db: Session = Depends(get_db)
):
    neuer_code = code_generieren()
    gutschein = Gutschein(
        code=neuer_code,
        original_wert=wert,
        rest_wert=wert,
        empfaenger_name=empfaenger,
        absender_name=absender,
        widmung=widmung
    )
    db.add(gutschein)
    db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/admin/gutschein/einloesen", dependencies=[Depends(check_admin_session)])
def gutschein_einloesen(code: str = Form(...), betrag: float = Form(...), db: Session = Depends(get_db)):
    gutschein = db.query(Gutschein).filter(Gutschein.code == code.strip().upper()).first()
    if gutschein and gutschein.rest_wert >= betrag:
        gutschein.rest_wert -= betrag
        db.commit()
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

# --- SHOP & CHECKOUT ---
@app.post("/shop/kaufen")
def shop_kaufen(
    wert: float = Form(...),
    empfaenger: str = Form(""),
    absender: str = Form(""),
    widmung: str = Form(""),
    db: Session = Depends(get_db)
):
    neuer_code = code_generieren()
    gutschein = Gutschein(
        code=neuer_code,
        original_wert=wert,
        rest_wert=wert,
        empfaenger_name=empfaenger,
        absender_name=absender,
        widmung=widmung
    )
    db.add(gutschein)
    db.commit()

    pdf_bytes = gutschein_pdf_erstellen(neuer_code, wert, empfaenger, absender, widmung)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Gutschein_{neuer_code}.pdf"})

@app.post("/shop/checkout")
def create_checkout_session(
    wert: float = Form(...),
    empfaenger: str = Form(""),
    absender: str = Form(""),
    widmung: str = Form(""),
    db: Session = Depends(get_db)
):
    # LOKALER TEST-MODUS (Ohne echten Stripe Key)
    if getattr(stripe, "api_key", None) in ["sk_test_12345", None, ""]:
        neuer_code = code_generieren()
        gutschein = Gutschein(
            code=neuer_code,
            original_wert=wert,
            rest_wert=wert,
            empfaenger_name=empfaenger,
            absender_name=absender,
            widmung=widmung
        )
        db.add(gutschein)
        db.commit()

        pdf_bytes = gutschein_pdf_erstellen(neuer_code, wert, empfaenger, absender, widmung)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Gutschein_{neuer_code}.pdf"}
        )

    # MIT ECHTEM STRIPE KEY (Für Produktion)
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': 'Hotel Wertgutschein'},
                    'unit_amount': int(wert * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            metadata={
                "wert": str(wert),
                "empfaenger": empfaenger,
                "absender": absender,
                "widmung": widmung
            },
            success_url="https://hotel-gutschein-system.onrender.com/shop/erfolg?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://hotel-gutschein-system.onrender.com/shop",
        )
        return RedirectResponse(url=checkout_session.url, status_code=303)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/shop/erfolg")
def shop_erfolg(request: Request, session_id: str, db: Session = Depends(get_db)):
    session = stripe.checkout.Session.retrieve(session_id)
    meta = session.metadata

    neuer_code = code_generieren()
    gutschein = Gutschein(
        code=neuer_code,
        original_wert=float(meta['wert']),
        rest_wert=float(meta['wert']),
        empfaenger_name=meta.get('empfaenger'),
        absender_name=meta.get('absender'),
        widmung=meta.get('widmung')
    )
    db.add(gutschein)
    db.commit()

    pdf_bytes = gutschein_pdf_erstellen(
        neuer_code,
        float(meta['wert']),
        meta.get('empfaenger', ''),
        meta.get('absender', ''),
        meta.get('widmung', '')
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Gutschein_{neuer_code}.pdf"}
    )
