# ============================================================
#  TEKZIVO — Flask + MySQL Backend API
#  File: app.py
#
#  Install dependencies:
#    pip install flask flask-sqlalchemy flask-cors pymysql python-dotenv
#
#  Create a .env file in the same folder:
#    DB_HOST=localhost
#    DB_PORT=3306
#    DB_USER=root
#    DB_PASSWORD=your_password
#    DB_NAME=tekzivo
#    SECRET_KEY=change_this_to_a_random_string
#
#  Run:
#    python app.py
#  API will be live at: http://localhost:5000
# ============================================================

import os
import uuid
import random
from datetime import datetime, date
from dotenv import load_dotenv

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import text

load_dotenv()

# ─────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────
app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)  # Allow requests from your HTML frontend

# Use SQLite exclusively (Free, Serverless & Config-Free for both local & PythonAnywhere)
db_path = os.path.join(os.path.dirname(__file__), "tekzivo.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "tekzivo-secret-key")

db = SQLAlchemy(app)

import gzip
import io

# ─────────────────────────────────────────
# GZIP COMPRESSION MIDDLEWARE
# ─────────────────────────────────────────
@app.after_request
def compress(response):
    if response.direct_passthrough:
        return response

    accept_encoding = request.headers.get("Accept-Encoding", "")
    if "gzip" not in accept_encoding.lower():
        return response

    if "Content-Encoding" in response.headers:
        return response

    content_type = response.headers.get("Content-Type", "")
    if not any(t in content_type for t in ["json", "html", "css", "javascript"]):
        return response

    response_data = response.get_data()
    if len(response_data) < 500:
        return response

    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(mode="wb", fileobj=gzip_buffer) as gzip_file:
        gzip_file.write(response_data)

    compressed_data = gzip_buffer.getvalue()
    if len(compressed_data) >= len(response_data):
        return response

    response.set_data(compressed_data)
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = len(compressed_data)
    return response


# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────
class ServiceArea(db.Model):
    __tablename__ = "service_areas"
    id         = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    pincode    = db.Column(db.String(10),  nullable=False, unique=True)
    city       = db.Column(db.String(100), nullable=False)
    state      = db.Column(db.String(100), nullable=False)
    is_active  = db.Column(db.Boolean,     nullable=False, default=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "pincode": self.pincode,
                "city": self.city, "state": self.state}


class Service(db.Model):
    __tablename__ = "services"
    id            = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    name          = db.Column(db.String(150), nullable=False)
    device_type   = db.Column(db.String(100), nullable=False, index=True)
    issue_type    = db.Column(db.String(150), nullable=False)
    base_price    = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    duration_mins = db.Column(db.Integer,     nullable=False, default=60)
    is_active     = db.Column(db.Boolean,     nullable=False, default=True)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "device_type": self.device_type, "issue_type": self.issue_type,
            "base_price": float(self.base_price),
            "duration_mins": self.duration_mins
        }


class Customer(db.Model):
    __tablename__ = "customers"
    id         = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = db.Column(db.String(150), nullable=False, index=True)
    phone      = db.Column(db.String(15),  nullable=False, unique=True)
    email      = db.Column(db.String(200), nullable=True)
    pincode    = db.Column(db.String(10),  nullable=False)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
    updated_at = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)
    bookings   = db.relationship("Booking", backref="customer", lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name,
            "phone": self.phone, "email": self.email,
            "pincode": self.pincode,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Technician(db.Model):
    __tablename__ = "technicians"
    id             = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    name           = db.Column(db.String(150), nullable=False)
    phone          = db.Column(db.String(15),  nullable=False, unique=True)
    email          = db.Column(db.String(200), nullable=True)
    specialization = db.Column(db.String(200), nullable=False)
    area_pincode   = db.Column(db.String(10),  nullable=False)
    rating         = db.Column(db.Numeric(3, 2), nullable=False, default=5.00)
    total_jobs     = db.Column(db.Integer,     nullable=False, default=0)
    is_available   = db.Column(db.Boolean,     nullable=False, default=True)
    is_active      = db.Column(db.Boolean,     nullable=False, default=True)
    created_at     = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "phone": self.phone,
            "specialization": self.specialization,
            "area_pincode": self.area_pincode,
            "rating": float(self.rating),
            "total_jobs": self.total_jobs,
            "is_available": self.is_available
        }


class Booking(db.Model):
    __tablename__ = "bookings"
    id                = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_ref       = db.Column(db.String(20),  nullable=False, unique=True)
    customer_id       = db.Column(db.String(36),  db.ForeignKey("customers.id"),   nullable=False, index=True)
    service_id        = db.Column(db.String(36),  db.ForeignKey("services.id"),    nullable=False, index=True)
    technician_id     = db.Column(db.String(36),  db.ForeignKey("technicians.id"), nullable=True, index=True)
    status            = db.Column(db.Enum("Pending","Confirmed","In Progress","Completed","Cancelled"),
                                  nullable=False, default="Pending", index=True)
    preferred_date    = db.Column(db.Date,        nullable=False, index=True)
    time_slot         = db.Column(db.String(30),  nullable=False)
    issue_description = db.Column(db.Text,        nullable=True)
    image_path        = db.Column(db.String(255), nullable=True)
    estimated_price   = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    final_price       = db.Column(db.Numeric(10, 2), nullable=True)
    address           = db.Column(db.Text,        nullable=True)
    pincode           = db.Column(db.String(10),  nullable=False, index=True)
    notes             = db.Column(db.Text,        nullable=True)
    booked_at         = db.Column(db.DateTime,    default=datetime.utcnow, index=True)
    updated_at        = db.Column(db.DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    service    = db.relationship("Service",    backref="bookings", lazy=True)
    technician = db.relationship("Technician", backref="bookings", lazy=True)
    payments   = db.relationship("Payment",    backref="booking",  lazy=True)

    def to_dict(self):
        return {
            "id":                self.id,
            "booking_ref":       self.booking_ref,
            "status":            self.status,
            "preferred_date":    self.preferred_date.isoformat() if self.preferred_date else None,
            "time_slot":         self.time_slot,
            "issue_description": self.issue_description,
            "image_path":        self.image_path,
            "estimated_price":   float(self.estimated_price),
            "final_price":       float(self.final_price) if self.final_price else None,
            "pincode":           self.pincode,
            "address":           self.address,
            "booked_at":         self.booked_at.isoformat() if self.booked_at else None,
            "updated_at":        self.updated_at.isoformat() if self.updated_at else None,
            "customer":          self.customer.to_dict() if self.customer else None,
            "service":           self.service.to_dict()  if self.service  else None,
            "technician":        self.technician.to_dict() if self.technician else None,
        }


class Payment(db.Model):
    __tablename__ = "payments"
    id             = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id     = db.Column(db.String(36), db.ForeignKey("bookings.id"), nullable=False)
    amount         = db.Column(db.Numeric(10, 2), nullable=False)
    method         = db.Column(db.Enum("Cash","UPI","Card","NetBanking","Wallet"), default="Cash")
    status         = db.Column(db.Enum("Pending","Paid","Failed","Refunded"), default="Pending")
    transaction_id = db.Column(db.String(100), nullable=True)
    paid_at        = db.Column(db.DateTime, nullable=True)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id, "booking_id": self.booking_id,
            "amount": float(self.amount), "method": self.method,
            "status": self.status, "transaction_id": self.transaction_id,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None
        }

class Brand(db.Model):
    __tablename__ = "brands"
    id         = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    name       = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class DeviceModel(db.Model):
    __tablename__ = "device_models"
    id          = db.Column(db.String(36),  primary_key=True, default=lambda: str(uuid.uuid4()))
    brand_id    = db.Column(db.String(36),  db.ForeignKey("brands.id"), nullable=False, index=True)
    name        = db.Column(db.String(150), nullable=False)
    device_type = db.Column(db.String(100), nullable=False, index=True)
    created_at  = db.Column(db.DateTime,    default=datetime.utcnow)

    brand = db.relationship("Brand", backref="models", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "brand_name": self.brand.name if self.brand else None,
            "name": self.name,
            "device_type": self.device_type
        }


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def generate_ref():
    year = datetime.utcnow().year
    rand = random.randint(10000, 99999)
    return f"TKZ-{year}-{rand}"

def ok(data, code=200):
    return jsonify({"success": True,  "data": data}), code

def err(msg, code=400):
    return jsonify({"success": False, "error": msg}), code


# ─────────────────────────────────────────
# ROUTES — BOOKINGS
# ─────────────────────────────────────────

# POST /api/bookings  — create a new booking (called from booking form)
@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json()

    required = ["name", "phone", "pincode", "device_type", "issue_type",
                "preferred_date", "time_slot"]
    for field in required:
        if not data.get(field):
            return err(f"'{field}' is required")

    # Get or create customer
    customer = Customer.query.filter_by(phone=data["phone"]).first()
    if not customer:
        customer = Customer(
            name    = data["name"],
            phone   = data["phone"],
            email   = data.get("email"),
            pincode = data["pincode"]
        )
        db.session.add(customer)
        db.session.flush()
    else:
        # Update existing customer details with the latest submission info
        customer.name = data["name"]
        if "email" in data:
            customer.email = data["email"]
        customer.pincode = data["pincode"]

    # Find matching service
    service = None
    if data.get("service_id"):
        service = Service.query.get(data["service_id"])

    if not service:
        service = Service.query.filter_by(
            device_type = data["device_type"],
            issue_type  = data.get("issue_type"),
            is_active   = True
        ).first()

    # If no exact match, pick first service for that device
    if not service:
        service = Service.query.filter_by(
            device_type = data["device_type"],
            is_active   = True
        ).first()

    if not service:
        return err("No service found for the selected device type")

    # Parse date
    try:
        pref_date = datetime.strptime(data["preferred_date"], "%Y-%m-%d").date()
    except ValueError:
        return err("Invalid date format. Use YYYY-MM-DD")

    est_price = float(data.get("estimated_price", service.base_price))

    booking = Booking(
        booking_ref       = generate_ref(),
        customer_id       = customer.id,
        service_id        = service.id,
        status            = "Pending",
        preferred_date    = pref_date,
        time_slot         = data["time_slot"],
        issue_description = data.get("issue_description", ""),
        image_path        = data.get("image_path"),
        estimated_price   = est_price,
        pincode           = data["pincode"],
        address           = data.get("address", "")
    )
    db.session.add(booking)
    db.session.flush()  # ← This generates booking.id before payment

    # Create a pending payment record
    payment = Payment(
        booking_id = booking.id,
        amount     = est_price,
        method     = "Cash",
        status     = "Pending"
    )
    db.session.add(payment)

    db.session.commit()
    return ok({"booking_ref": booking.booking_ref, "booking": booking.to_dict()}, 201)


# GET /api/bookings  — list all bookings (admin portal)
@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    status  = request.args.get("status")
    search  = request.args.get("search", "").strip()
    page    = int(request.args.get("page", 1))
    per_page= int(request.args.get("per_page", 20))

    query = Booking.query

    if status:
        query = query.filter(Booking.status == status)

    if search:
        query = query.join(Customer).filter(
            db.or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%"),
                Booking.booking_ref.ilike(f"%{search}%"),
                Booking.pincode.ilike(f"%{search}%")
            )
        )

    query = query.order_by(Booking.booked_at.desc())
    total = query.count()
    bookings = query.offset((page - 1) * per_page).limit(per_page).all()

    return ok({
        "bookings": [b.to_dict() for b in bookings],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    })


# GET /api/bookings/<id>  — single booking detail
@app.route("/api/bookings/<booking_id>", methods=["GET"])
def get_booking(booking_id):
    b = Booking.query.filter(
        db.or_(Booking.id == booking_id, Booking.booking_ref == booking_id)
    ).first()
    if not b:
        return err("Booking not found", 404)
    return ok(b.to_dict())


# PATCH /api/bookings/<id>/status  — update status (admin portal)
@app.route("/api/bookings/<booking_id>/status", methods=["PATCH"])
def update_status(booking_id):
    b = Booking.query.filter(
        db.or_(Booking.id == booking_id, Booking.booking_ref == booking_id)
    ).first()
    if not b:
        return err("Booking not found", 404)

    data       = request.get_json()
    new_status = data.get("status")
    valid      = ["Pending", "Confirmed", "In Progress", "Completed", "Cancelled"]
    if new_status not in valid:
        return err(f"Invalid status. Must be one of: {', '.join(valid)}")

    b.status     = new_status
    b.updated_at = datetime.utcnow()

    if data.get("technician_id"):
        b.technician_id = data["technician_id"]

    if data.get("final_price"):
        b.final_price = data["final_price"]

    db.session.commit()
    return ok(b.to_dict())


# PATCH /api/bookings/<id>/assign  — assign technician
@app.route("/api/bookings/<booking_id>/assign", methods=["PATCH"])
def assign_technician(booking_id):
    b = Booking.query.get(booking_id)
    if not b:
        return err("Booking not found", 404)

    data = request.get_json()
    tech = Technician.query.get(data.get("technician_id"))
    if not tech:
        return err("Technician not found", 404)

    b.technician_id = tech.id
    b.status        = "Confirmed"
    db.session.commit()
    return ok(b.to_dict())


# DELETE /api/bookings/<id>  — cancel booking
@app.route("/api/bookings/<booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    b = Booking.query.filter(
        db.or_(Booking.id == booking_id, Booking.booking_ref == booking_id)
    ).first()
    if not b:
        return err("Booking not found", 404)
    b.status = "Cancelled"
    db.session.commit()
    return ok({"message": "Booking cancelled", "booking_ref": b.booking_ref})


# ─────────────────────────────────────────
# ROUTES — SERVICES
# ─────────────────────────────────────────

@app.route("/api/services", methods=["GET"])
def get_services():
    device = request.args.get("device_type")
    include_inactive = request.args.get("all") == "true"
    
    if include_inactive:
        query = Service.query
    else:
        query = Service.query.filter_by(is_active=True)
        
    if device:
        query = query.filter_by(device_type=device)
    return ok([s.to_dict() for s in query.all()])

@app.route("/api/services", methods=["POST"])
def add_service():
    data = request.get_json()
    required = ["name", "device_type", "issue_type", "base_price"]
    for field in required:
        if not data.get(field):
            return err(f"'{field}' is required")
    try:
        price = float(data["base_price"])
    except ValueError:
        return err("base_price must be a number")

    service = Service(
        name=data["name"],
        device_type=data["device_type"],
        issue_type=data["issue_type"],
        base_price=price,
        duration_mins=int(data.get("duration_mins", 60)),
        is_active=True
    )
    db.session.add(service)
    db.session.commit()
    return ok(service.to_dict(), 201)

@app.route("/api/services/<service_id>", methods=["PATCH"])
def update_service(service_id):
    service = Service.query.get(service_id)
    if not service:
        return err("Service not found", 404)
    data = request.get_json()
    if "name" in data:
        service.name = data["name"]
    if "device_type" in data:
        service.device_type = data["device_type"]
    if "issue_type" in data:
        service.issue_type = data["issue_type"]
    if "base_price" in data:
        try:
            service.base_price = float(data["base_price"])
        except ValueError:
            return err("base_price must be a number")
    if "duration_mins" in data:
        service.duration_mins = int(data["duration_mins"])
    if "is_active" in data:
        service.is_active = bool(data["is_active"])

    db.session.commit()
    return ok(service.to_dict())

@app.route("/api/services/<service_id>", methods=["DELETE"])
def delete_service(service_id):
    service = Service.query.get(service_id)
    if not service:
        return err("Service not found", 404)
    db.session.delete(service)
    db.session.commit()
    return ok({"message": "Service deleted successfully"})


# ─────────────────────────────────────────
# ROUTES — BRANDS & MODELS
# ─────────────────────────────────────────

@app.route("/api/brands", methods=["GET"])
def get_brands():
    brands = Brand.query.order_by(Brand.name).all()
    return ok([b.to_dict() for b in brands])

@app.route("/api/brands", methods=["POST"])
def add_brand():
    data = request.get_json()
    if not data.get("name"):
        return err("Brand name is required")
    brand = Brand(name=data["name"])
    db.session.add(brand)
    try:
        db.session.commit()
        return ok(brand.to_dict(), 201)
    except Exception as e:
        db.session.rollback()
        return err("Brand might already exist")

@app.route("/api/brands/<brand_id>", methods=["DELETE"])
def delete_brand(brand_id):
    b = Brand.query.get(brand_id)
    if b:
        DeviceModel.query.filter_by(brand_id=brand_id).delete()
        db.session.delete(b)
        db.session.commit()
    return ok({"message": "Brand deleted"})

@app.route("/api/models", methods=["GET"])
def get_models():
    brand_id = request.args.get("brand_id")
    device_type = request.args.get("device_type")
    query = DeviceModel.query
    if brand_id:
        query = query.filter_by(brand_id=brand_id)
    if device_type:
        query = query.filter_by(device_type=device_type)
    models = query.order_by(DeviceModel.name).all()
    return ok([m.to_dict() for m in models])

@app.route("/api/models", methods=["POST"])
def add_model():
    data = request.get_json()
    if not data.get("brand_id") or not data.get("name") or not data.get("device_type"):
        return err("brand_id, name, and device_type are required")
    m = DeviceModel(brand_id=data["brand_id"], name=data["name"], device_type=data["device_type"])
    db.session.add(m)
    db.session.commit()
    return ok(m.to_dict(), 201)

@app.route("/api/models/<model_id>", methods=["DELETE"])
def delete_model(model_id):
    m = DeviceModel.query.get(model_id)
    if m:
        db.session.delete(m)
        db.session.commit()
    return ok({"message": "Model deleted"})


# ─────────────────────────────────────────
# ROUTES — CUSTOMERS
# ─────────────────────────────────────────

@app.route("/api/customers", methods=["GET"])
def get_customers():
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))
    search   = request.args.get("search", "").strip()

    query = Customer.query
    if search:
        query = query.filter(
            db.or_(
                Customer.name.ilike(f"%{search}%"),
                Customer.phone.ilike(f"%{search}%")
            )
        )
    query = query.order_by(Customer.created_at.desc())
    total = query.count()
    customers = query.offset((page - 1) * per_page).limit(per_page).all()

    return ok({
        "customers": [c.to_dict() for c in customers],
        "total": total
    })


# ─────────────────────────────────────────
# ROUTES — TECHNICIANS
# ─────────────────────────────────────────

@app.route("/api/technicians", methods=["GET"])
def get_technicians():
    available_only = request.args.get("available") == "true"
    query = Technician.query.filter_by(is_active=True)
    if available_only:
        query = query.filter_by(is_available=True)
    return ok([t.to_dict() for t in query.all()])


# ─────────────────────────────────────────
# ROUTES — DASHBOARD STATS & BOOTSTRAPPING
# ─────────────────────────────────────────

def _get_dashboard_stats_raw():
    total      = Booking.query.count()
    pending    = Booking.query.filter_by(status="Pending").count()
    confirmed  = Booking.query.filter_by(status="Confirmed").count()
    inprogress = Booking.query.filter_by(status="In Progress").count()
    completed  = Booking.query.filter_by(status="Completed").count()
    cancelled  = Booking.query.filter_by(status="Cancelled").count()

    # Revenue: sum of completed bookings
    from sqlalchemy import func
    revenue = db.session.query(func.coalesce(func.sum(Booking.estimated_price), 0)).filter(Booking.status == 'Completed').scalar()
    revenue = float(revenue)

    # Avg rating across technicians
    avg_rating = db.session.query(func.coalesce(func.avg(Technician.rating), 0)).filter(Technician.is_active == True).scalar()

    # Top technicians
    top_techs = db.session.query(
        Technician.name, Technician.specialization, Technician.rating, Technician.total_jobs
    ).filter(Technician.is_active == True).order_by(Technician.total_jobs.desc()).limit(5).all()

    # Bookings per day (last 7 days) — SQLite query
    daily = db.session.execute(text("""
        SELECT date(booked_at) AS day, COUNT(*) AS count
        FROM bookings
        WHERE booked_at >= date('now', '-7 days')
        GROUP BY date(booked_at)
        ORDER BY day ASC
    """)).fetchall()

    return {
        "totals": {
            "total": total, "pending": pending, "confirmed": confirmed,
            "in_progress": inprogress, "completed": completed, "cancelled": cancelled
        },
        "revenue": revenue,
        "avg_rating": round(float(avg_rating or 0), 2),
        "top_technicians": [
            {"name": r[0], "specialization": r[1],
             "rating": float(r[2]), "total_jobs": r[3]}
            for r in top_techs
        ],
        "daily_bookings": [
            {"date": str(r[0]), "count": r[1]} for r in daily
        ]
    }


@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    try:
        return ok(_get_dashboard_stats_raw())
    except Exception as e:
        return err(f"Failed to load dashboard stats: {str(e)}", 500)


@app.route("/api/bootstrap", methods=["GET"])
def api_bootstrap():
    try:
        # Load settings
        settings = load_settings()
        
        # Load brands
        brands = [b.to_dict() for b in Brand.query.order_by(Brand.name).all()]
        
        # Load models
        models = [m.to_dict() for m in DeviceModel.query.order_by(DeviceModel.name).all()]
        
        # Load services
        services = [s.to_dict() for s in Service.query.filter_by(is_active=True).all()]
        
        return ok({
            "settings": settings,
            "brands": brands,
            "models": models,
            "services": services
        })
    except Exception as e:
        return err(f"Bootstrap failed: {str(e)}", 500)


@app.route("/api/admin/bootstrap", methods=["GET"])
def api_admin_bootstrap():
    try:
        # Load technicians
        techs = [t.to_dict() for t in Technician.query.filter_by(is_active=True).all()]
        
        # Load stats
        stats = _get_dashboard_stats_raw()
        
        # Load bookings (first page/recent ones, equivalent to get_bookings with per_page=200)
        bookings_query = Booking.query.order_by(Booking.booked_at.desc()).limit(200).all()
        bookings = [b.to_dict() for b in bookings_query]
        
        return ok({
            "technicians": techs,
            "stats": stats,
            "bookings": bookings
        })
    except Exception as e:
        return err(f"Admin bootstrap failed: {str(e)}", 500)


# ─────────────────────────────────────────
# ROUTES — SERVICE AREAS (check coverage)
# ─────────────────────────────────────────

@app.route("/api/check-pincode/<pincode>", methods=["GET"])
def check_pincode(pincode):
    area = ServiceArea.query.filter_by(pincode=pincode, is_active=True).first()
    if area:
        return ok({"covered": True,  "city": area.city, "state": area.state})
    return ok({"covered": False, "message": "Sorry, we don't serve this pincode yet."})


# ─────────────────────────────────────────
# ROUTES — SETTINGS & SERVICE AREAS
# ─────────────────────────────────────────

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

def load_settings():
    import json
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {
        "business_name": "Tekzivo Electronics Care",
        "support_phone": "+91 98765 43210",
        "support_email": "support@tekzivo.com",
        "business_hours": "09:00 AM - 07:00 PM"
    }

def save_settings(settings):
    import json
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except:
        return False

@app.route("/api/settings", methods=["GET"])
def get_settings():
    return ok(load_settings())

@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.json or {}
    settings = load_settings()
    settings.update(data)
    if save_settings(settings):
        return ok(settings)
    return err("Failed to save settings", 500)

@app.route("/api/service-areas", methods=["GET"])
def get_service_areas():
    areas = ServiceArea.query.order_by(ServiceArea.pincode).all()
    return ok([a.to_dict() for a in areas])

@app.route("/api/service-areas", methods=["POST"])
def add_service_area():
    data = request.json or {}
    pincode = data.get("pincode")
    city = data.get("city")
    state = data.get("state")
    if not pincode or not city or not state:
        return err("Missing pincode, city, or state")
    
    # Check if pincode already exists
    existing = ServiceArea.query.filter_by(pincode=pincode).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.city = city
            existing.state = state
            db.session.commit()
            return ok(existing.to_dict())
        return err("Pincode already registered")
        
    area = ServiceArea(pincode=pincode, city=city, state=state, is_active=True)
    db.session.add(area)
    db.session.commit()
    return ok(area.to_dict())

@app.route("/api/service-areas/<area_id>", methods=["DELETE"])
def delete_service_area(area_id):
    area = ServiceArea.query.get(area_id)
    if not area:
        return err("Service area not found", 404)
    db.session.delete(area)
    db.session.commit()
    return ok({"message": "Service area deleted"})


# ─────────────────────────────────────────
# ROUTES — UPLOADS
# ─────────────────────────────────────────

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return err("No file part", 400)
    file = request.files["file"]
    if file.filename == "":
        return err("No selected file", 400)
    
    # Allow safe image formats
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_extensions:
        return err("Invalid file type. Only images are allowed.", 400)
    
    # Ensure uploads folder exists in static directory
    uploads_dir = os.path.join(app.static_folder, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Save the file with a unique name
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(uploads_dir, unique_filename)
    file.save(file_path)
    
    return ok({"file_path": f"/uploads/{unique_filename}"})


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return ok({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def seed_default_brands_and_models():
    # Only seed if there are no brands currently in the database
    if Brand.query.first():
        return

    BRAND_MODELS = {
        'Smartphone': [
            'Apple iPhone 13', 'Apple iPhone 14', 'Apple iPhone 15', 'Apple iPhone 12',
            'Samsung Galaxy S22', 'Samsung Galaxy S23', 'Samsung Galaxy S24',
            'OnePlus 10 Pro', 'OnePlus 11', 'OnePlus 12',
            'Xiaomi Redmi Note 12', 'Xiaomi 13 Pro', 'Google Pixel 7', 'Google Pixel 8'
        ],
        'Laptop': [
            'Apple MacBook Air M1', 'Apple MacBook Pro M2', 'Apple MacBook Pro M3',
            'HP Pavilion 15', 'HP Envy x360', 'HP Spectre x360',
            'Dell XPS 13', 'Dell Inspiron 15', 'Dell Alienware m15',
            'Lenovo ThinkPad X1', 'Lenovo IdeaPad 3', 'Lenovo Legion 5'
        ],
        'LED TV': [
            'Samsung 55" Crystal 4K', 'Samsung 65" QLED', 'Samsung 43" Smart TV',
            'LG 55" OLED', 'LG 43" UHD', 'LG 65" NanoCell',
            'Sony Bravia 55" 4K', 'Sony Bravia 65" OLED',
            'OnePlus 50" Y Series', 'Xiaomi Mi TV 5X 43"'
        ]
    }

    brand_objs = {}
    for device_type, items in BRAND_MODELS.items():
        for item in items:
            parts = item.split(" ", 1)
            brand_name = parts[0]
            model_name = parts[1] if len(parts) > 1 else ""

            # Get or create brand
            if brand_name not in brand_objs:
                b = Brand.query.filter_by(name=brand_name).first()
                if not b:
                    b = Brand(name=brand_name)
                    db.session.add(b)
                    db.session.flush() # get ID
                brand_objs[brand_name] = b
            
            b_id = brand_objs[brand_name].id

            # Create model if not exists
            m = DeviceModel.query.filter_by(brand_id=b_id, name=model_name, device_type=device_type).first()
            if not m:
                m = DeviceModel(brand_id=b_id, name=model_name, device_type=device_type)
                db.session.add(m)
    
    db.session.commit()
    print("[SUCCESS] Seeded default brands and models into the database.")

def seed_default_services_and_areas():
    # 1. Seed Service Areas
    if not ServiceArea.query.first():
        areas = [
            ServiceArea(pincode="600001", city="Chennai", state="Tamil Nadu"),
            ServiceArea(pincode="600002", city="Chennai", state="Tamil Nadu"),
            ServiceArea(pincode="560001", city="Bangalore", state="Karnataka"),
            ServiceArea(pincode="400001", city="Mumbai", state="Maharashtra"),
            ServiceArea(pincode="682001", city="Kochi", state="Kerala"),
            ServiceArea(pincode="500001", city="Hyderabad", state="Telangana")
        ]
        db.session.bulk_save_objects(areas)
        print("[SEED] Service areas seeded.")

    # 2. Seed Services Catalog
    if not Service.query.first():
        services = [
            Service(name="Screen Replacement", device_type="Smartphone", issue_type="Cracked Screen", base_price=1800.00, duration_mins=60),
            Service(name="Battery Replacement", device_type="Smartphone", issue_type="Battery Draining", base_price=799.00, duration_mins=45),
            Service(name="Charging Port Fix", device_type="Smartphone", issue_type="Not Charging", base_price=650.00, duration_mins=45),
            Service(name="Laptop Screen Fix", device_type="Laptop", issue_type="Screen Damage", base_price=2500.00, duration_mins=90),
            Service(name="Keyboard Repair", device_type="Laptop", issue_type="Keys Not Working", base_price=1350.00, duration_mins=60),
            Service(name="Motherboard Repair", device_type="Laptop", issue_type="Not Turning On", base_price=3500.00, duration_mins=120),
            Service(name="TV Panel Repair", device_type="LED TV", issue_type="No Display", base_price=1500.00, duration_mins=90),
            Service(name="TV Sound Fix", device_type="LED TV", issue_type="Sound Issue", base_price=800.00, duration_mins=60)
        ]
        db.session.bulk_save_objects(services)
        print("[SEED] Services catalog seeded.")

    # 3. Seed Technicians
    if not Technician.query.first():
        technicians = [
            Technician(name="Rajan M", phone="+91 98765 11111", specialization="Mobile & Laptop", area_pincode="600001", rating=4.9, total_jobs=42),
            Technician(name="Vijay K", phone="+91 98765 22222", specialization="AC & Appliances", area_pincode="560001", rating=4.8, total_jobs=38),
            Technician(name="Kumar R", phone="+91 98765 33333", specialization="TV & Electronics", area_pincode="400001", rating=4.7, total_jobs=31)
        ]
        db.session.bulk_save_objects(technicians)
        print("[SEED] Technicians seeded.")

    db.session.commit()
    print("[SUCCESS] Seeded default services, areas, and technicians into the database.")

@app.route("/")
@app.route("/booking")
def index():
    return app.send_static_file("index.html")

@app.route("/admin")
def admin():
    return app.send_static_file("admin/index.html")


def create_indexes():
    # Attempt to add image_path column if it doesn't exist (SQLite migration fallback)
    try:
        db.session.execute(text("ALTER TABLE bookings ADD COLUMN image_path TEXT;"))
        db.session.commit()
    except Exception:
        db.session.rollback()

    # SQLite-specific raw CREATE INDEX statements for robustness
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);",
        "CREATE INDEX IF NOT EXISTS idx_bookings_booked_at ON bookings(booked_at);",
        "CREATE INDEX IF NOT EXISTS idx_bookings_customer_id ON bookings(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_bookings_technician_id ON bookings(technician_id);",
        "CREATE INDEX IF NOT EXISTS idx_bookings_service_id ON bookings(service_id);",
        "CREATE INDEX IF NOT EXISTS idx_bookings_pincode ON bookings(pincode);",
        "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name);",
        "CREATE INDEX IF NOT EXISTS idx_services_device_type ON services(device_type);",
        "CREATE INDEX IF NOT EXISTS idx_device_models_brand_id ON device_models(brand_id);",
        "CREATE INDEX IF NOT EXISTS idx_device_models_device_type ON device_models(device_type);"
    ]
    for stmt in statements:
        try:
            db.session.execute(text(stmt))
        except Exception as e:
            print(f"[INDEX ERROR] Failed to create index: {e}")
    db.session.commit()

# Ensure tables are created and indexed on import / startup
with app.app_context():
    db.create_all()
    create_indexes()

if __name__ == "__main__":
    with app.app_context():
        seed_default_brands_and_models()
        seed_default_services_and_areas()
    print("[SUCCESS] Tekzivo API running at http://localhost:5000")
    app.run(debug=True, host="0.0.0.0", port=5000)
