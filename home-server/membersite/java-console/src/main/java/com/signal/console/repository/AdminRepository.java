package com.signal.console.repository;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/** Administrator credentials. Only BCrypt hashes are stored, never plaintext. */
@Repository
public class AdminRepository {

    private final JdbcTemplate jdbc;

    public AdminRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    public boolean exists() {
        Integer n = jdbc.queryForObject("SELECT COUNT(*) FROM console_admins", Integer.class);
        return n != null && n > 0;
    }

    public String findHash(String username) {
        try {
            return jdbc.queryForObject(
                    "SELECT password_hash FROM console_admins WHERE username = ?",
                    String.class, username);
        } catch (Exception e) { return null; }
    }

    public void create(String username, String hash) {
        jdbc.update("INSERT INTO console_admins (username, password_hash, created_at) VALUES (?,?,?)",
                username, hash,
                LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")));
    }

    public void updateHash(String username, String hash) {
        jdbc.update("UPDATE console_admins SET password_hash = ? WHERE username = ?",
                hash, username);
    }
}
