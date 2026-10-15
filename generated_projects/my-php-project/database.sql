CREATE DATABASE IF NOT EXISTS `auth_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE `auth_db`;

CREATE TABLE IF NOT EXISTS `users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `full_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(150) NOT NULL,
  `password` VARCHAR(255) NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initial Demo User (Password: Password123!)
INSERT INTO `users` (`full_name`, `email`, `password`, `created_at`) 
VALUES (
  'Demo User', 
  'user@example.com', 
  '$2y$12$eAn7Q2O5U4Esk3/X1tGv/.GkH9s/Y8p50d.z41G1q44kX88JjT7eC', 
  NOW()
) ON DUPLICATE KEY UPDATE `id`=`id`;
     mysql -u root -p < database.sql
     php -S localhost:8000