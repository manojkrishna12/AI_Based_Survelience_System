-- SQLite Schema for AI Based Smart Surveillance System

-- Drop tables if they exist
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS cameras;
DROP TABLE IF EXISTS users;

-- 1. Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'operator',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Cameras Table
CREATE TABLE cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source TEXT NOT NULL, -- e.g., '0' for Webcam, or video path, or 'RTSP/...'
    status TEXT DEFAULT 'active', -- 'active' or 'inactive'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Alerts Table
CREATE TABLE alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER,
    alert_type TEXT NOT NULL, -- 'Human', 'Face', 'Motion', 'Intrusion', 'Fire/Smoke'
    confidence REAL,
    image_path TEXT, -- path to screenshot capture
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
);
