-- TOOL-E core schema (MySQL)
-- Creates the tool_e_db database and the tools + transactions tables.

CREATE DATABASE IF NOT EXISTS tool_e_db;
USE tool_e_db;

CREATE TABLE IF NOT EXISTS tools (
    tool_id INT NOT NULL AUTO_INCREMENT,
    tool_name VARCHAR(255) NOT NULL,
    tool_size VARCHAR(50) NULL,
    tool_type VARCHAR(100) NOT NULL,
    current_status VARCHAR(50) NOT NULL DEFAULT 'Available',
    total_quantity INT NOT NULL DEFAULT 0,
    available_quantity INT NOT NULL DEFAULT 0,
    consumed_quantity INT NOT NULL DEFAULT 0,
    trained TINYINT(1) NOT NULL DEFAULT 0,
    image MEDIUMBLOB NULL,
    PRIMARY KEY (tool_id),
    INDEX idx_tools_name (tool_name),
    INDEX idx_tools_status (current_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id VARCHAR(64) NOT NULL,
    user_id INT NULL,
    tool_id INT NULL,
    checkout_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    desired_return_date DATETIME NULL,
    return_timestamp DATETIME NULL,
    quantity INT NOT NULL DEFAULT 1,
    purpose VARCHAR(255) NULL,
    image_path VARCHAR(255) NULL,
    classification_correct TINYINT(1) NULL,
    weight INT NOT NULL DEFAULT 0,
    user_name VARCHAR(255) NULL,
    return_image_path VARCHAR(255) NULL,
    PRIMARY KEY (transaction_id),
    INDEX idx_transactions_user_id (user_id),
    INDEX idx_transactions_tool_id (tool_id),
    INDEX idx_transactions_checkout_ts (checkout_timestamp),
    INDEX idx_transactions_return_ts (return_timestamp),
    CONSTRAINT fk_transactions_tool
        FOREIGN KEY (tool_id)
        REFERENCES tools (tool_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
