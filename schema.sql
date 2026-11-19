-- StockSense AI database schema (MySQL 5.7+ / 8.x)
CREATE DATABASE IF NOT EXISTS stocksense CHARACTER SET utf8mb4;
USE stocksense;

CREATE TABLE IF NOT EXISTS suppliers (
  supplier_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL UNIQUE,
  contact VARCHAR(120) NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
  product_id INT AUTO_INCREMENT PRIMARY KEY,
  product_name VARCHAR(150) NOT NULL,
  category VARCHAR(80) NOT NULL,
  stock_quantity INT NOT NULL DEFAULT 0,
  purchase_price DECIMAL(10,2) NOT NULL DEFAULT 0,
  selling_price DECIMAL(10,2) NOT NULL DEFAULT 0,
  supplier_id INT NULL,
  manufacturing_date DATE NULL,
  expiry_date DATE NOT NULL,
  min_stock_level INT NOT NULL DEFAULT 0,
  date_added DATE NOT NULL,
  is_sample TINYINT NOT NULL DEFAULT 0,
  FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales (
  sale_id INT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  quantity_sold INT NOT NULL,
  sale_date DATE NOT NULL,
  selling_price DECIMAL(10,2) NOT NULL,
  is_sample TINYINT NOT NULL DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_settings (
  setting_key VARCHAR(60) PRIMARY KEY,
  setting_value VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS model_runs (
  run_id INT AUTO_INCREMENT PRIMARY KEY,
  trained_at DATETIME NOT NULL,
  model_name VARCHAR(80) NOT NULL,
  train_rows INT NOT NULL,
  test_rows INT NOT NULL,
  mae DOUBLE NULL,
  rmse DOUBLE NULL,
  mape DOUBLE NULL,
  r2 DOUBLE NULL,
  notes TEXT NULL
)
