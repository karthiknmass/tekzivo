-- ============================================================
--  TEKZIVO DATABASE SCHEMA
--  MySQL 8.0+
--  Run: mysql -u root -p < schema.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS tekzivo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tekzivo;

-- ─────────────────────────────────────────
-- 1. SERVICE AREAS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS service_areas (
    id          CHAR(36)        NOT NULL DEFAULT (UUID()),
    pincode     VARCHAR(10)     NOT NULL UNIQUE,
    city        VARCHAR(100)    NOT NULL,
    state       VARCHAR(100)    NOT NULL,
    is_active   TINYINT(1)      NOT NULL DEFAULT 1,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_pincode (pincode)
);

-- ─────────────────────────────────────────
-- 2. SERVICES CATALOG
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS services (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    name            VARCHAR(150)    NOT NULL,
    device_type     VARCHAR(100)    NOT NULL,
    issue_type      VARCHAR(150)    NOT NULL,
    base_price      DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    duration_mins   INT             NOT NULL DEFAULT 60,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_device (device_type)
);

-- ─────────────────────────────────────────
-- 3. CUSTOMERS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
    id          CHAR(36)        NOT NULL DEFAULT (UUID()),
    name        VARCHAR(150)    NOT NULL,
    phone       VARCHAR(15)     NOT NULL UNIQUE,
    email       VARCHAR(200)    NULL,
    pincode     VARCHAR(10)     NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_phone  (phone),
    INDEX idx_pincode (pincode)
);

-- ─────────────────────────────────────────
-- 4. TECHNICIANS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS technicians (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    name            VARCHAR(150)    NOT NULL,
    phone           VARCHAR(15)     NOT NULL UNIQUE,
    email           VARCHAR(200)    NULL,
    specialization  VARCHAR(200)    NOT NULL,
    area_pincode    VARCHAR(10)     NOT NULL,
    rating          DECIMAL(3,2)    NOT NULL DEFAULT 5.00,
    total_jobs      INT             NOT NULL DEFAULT 0,
    is_available    TINYINT(1)      NOT NULL DEFAULT 1,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_pincode   (area_pincode),
    INDEX idx_available (is_available)
);

-- ─────────────────────────────────────────
-- 5. BOOKINGS  (core table)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bookings (
    id                  CHAR(36)        NOT NULL DEFAULT (UUID()),
    booking_ref         VARCHAR(20)     NOT NULL UNIQUE,
    customer_id         CHAR(36)        NOT NULL,
    service_id          CHAR(36)        NOT NULL,
    technician_id       CHAR(36)        NULL,
    status              ENUM(
                          'Pending',
                          'Confirmed',
                          'In Progress',
                          'Completed',
                          'Cancelled'
                        ) NOT NULL DEFAULT 'Pending',
    preferred_date      DATE            NOT NULL,
    time_slot           VARCHAR(30)     NOT NULL,
    issue_description   TEXT            NULL,
    estimated_price     DECIMAL(10,2)   NOT NULL DEFAULT 0.00,
    final_price         DECIMAL(10,2)   NULL,
    address             TEXT            NULL,
    pincode             VARCHAR(10)     NOT NULL,
    notes               TEXT            NULL,
    booked_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_status        (status),
    INDEX idx_customer      (customer_id),
    INDEX idx_technician    (technician_id),
    INDEX idx_date          (preferred_date),
    INDEX idx_ref           (booking_ref),
    CONSTRAINT fk_booking_customer   FOREIGN KEY (customer_id)   REFERENCES customers(id),
    CONSTRAINT fk_booking_service    FOREIGN KEY (service_id)    REFERENCES services(id),
    CONSTRAINT fk_booking_technician FOREIGN KEY (technician_id) REFERENCES technicians(id)
);

-- ─────────────────────────────────────────
-- 6. PAYMENTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id              CHAR(36)        NOT NULL DEFAULT (UUID()),
    booking_id      CHAR(36)        NOT NULL,
    amount          DECIMAL(10,2)   NOT NULL,
    method          ENUM('Cash','UPI','Card','NetBanking','Wallet') NOT NULL DEFAULT 'Cash',
    status          ENUM('Pending','Paid','Failed','Refunded')      NOT NULL DEFAULT 'Pending',
    transaction_id  VARCHAR(100)    NULL,
    paid_at         DATETIME        NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_booking (booking_id),
    INDEX idx_status  (status),
    CONSTRAINT fk_payment_booking FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

-- ============================================================
--  SAMPLE DATA
-- ============================================================

-- Service Areas
INSERT INTO service_areas (id, pincode, city, state) VALUES
  (UUID(), '600001', 'Chennai',   'Tamil Nadu'),
  (UUID(), '600002', 'Chennai',   'Tamil Nadu'),
  (UUID(), '560001', 'Bangalore', 'Karnataka'),
  (UUID(), '400001', 'Mumbai',    'Maharashtra'),
  (UUID(), '682001', 'Kochi',     'Kerala'),
  (UUID(), '500001', 'Hyderabad', 'Telangana');

-- Services Catalog
INSERT INTO services (id, name, device_type, issue_type, base_price, duration_mins) VALUES
  (UUID(), 'Screen Replacement',  'Smartphone',      'Cracked Screen',     1800.00, 60),
  (UUID(), 'Battery Replacement', 'Smartphone',      'Battery Draining',    799.00, 45),
  (UUID(), 'Charging Port Fix',   'Smartphone',      'Not Charging',        650.00, 45),
  (UUID(), 'Laptop Screen Fix',   'Laptop',          'Screen Damage',      2500.00, 90),
  (UUID(), 'Keyboard Repair',     'Laptop',          'Keys Not Working',   1350.00, 60),
  (UUID(), 'Motherboard Repair',  'Laptop',          'Not Turning On',     3500.00, 120),
  (UUID(), 'TV Panel Repair',     'LED TV',          'No Display',         1500.00, 90),
  (UUID(), 'TV Sound Fix',        'LED TV',          'Sound Issue',         800.00, 60);

-- Technicians
INSERT INTO technicians (id, name, phone, specialization, area_pincode, rating, total_jobs) VALUES
  (UUID(), 'Rajan M',  '+91 98765 11111', 'Mobile & Laptop',    '600001', 4.9, 42),
  (UUID(), 'Vijay K',  '+91 98765 22222', 'AC & Appliances',    '560001', 4.8, 38),
  (UUID(), 'Kumar R',  '+91 98765 33333', 'TV & Electronics',   '400001', 4.7, 31);

-- ============================================================
--  STORED PROCEDURE: Generate booking reference
-- ============================================================
DELIMITER $$
CREATE PROCEDURE IF NOT EXISTS generate_booking_ref(OUT ref VARCHAR(20))
BEGIN
    SET ref = CONCAT('TKZ-', YEAR(NOW()), '-', LPAD(FLOOR(RAND() * 99999), 5, '0'));
END$$
DELIMITER ;

-- ============================================================
--  VIEW: Bookings with full details (used by admin portal)
-- ============================================================
CREATE OR REPLACE VIEW v_bookings_detail AS
SELECT
    b.id,
    b.booking_ref,
    b.status,
    b.preferred_date,
    b.time_slot,
    b.issue_description,
    b.estimated_price,
    b.final_price,
    b.pincode,
    b.booked_at,
    b.updated_at,
    c.name        AS customer_name,
    c.phone       AS customer_phone,
    c.email       AS customer_email,
    s.name        AS service_name,
    s.device_type,
    s.issue_type,
    t.name        AS technician_name,
    t.phone       AS technician_phone,
    p.amount      AS payment_amount,
    p.method      AS payment_method,
    p.status      AS payment_status
FROM bookings b
JOIN customers   c ON c.id = b.customer_id
JOIN services    s ON s.id = b.service_id
LEFT JOIN technicians t ON t.id  = b.technician_id
LEFT JOIN payments    p ON p.booking_id = b.id;
