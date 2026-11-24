package com.signal.console.service;

import com.signal.console.config.ConsoleProperties;
import com.signal.console.repository.AdminRepository;
import jakarta.annotation.PostConstruct;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/** Administrator login + server-side sessions (in-memory; swap for Redis/Spring Session at scale). */
@Service
public class AuthService {

    private final AdminRepository repo;
    private final ConsoleProperties props;
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();
    private final ConcurrentHashMap<String, Session> sessions = new ConcurrentHashMap<>();
    private final SecureRandom random = new SecureRandom();

    private record Session(String user, long expiresAt) {}

    public AuthService(AdminRepository repo, ConsoleProperties props) {
        this.repo = repo; this.props = props;
    }

    /** First boot: generate a RANDOM password, write it to a gitignored local file. */
    @PostConstruct
    public void bootstrap() {
        if (repo.exists()) return;
        byte[] bytes = new byte[12];
        random.nextBytes(bytes);
        String password = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
        repo.create(props.getBootstrapUser(), encoder.encode(password));
        try {
            Path f = Path.of("data", "admin-credentials-java.txt");
            Files.createDirectories(f.getParent());
            Files.writeString(f,
                    "SIGNAL Java 管理后台初始凭据（请登录后立即修改，勿提交到 Git）\n"
                            + "账号:   " + props.getBootstrapUser() + "\n"
                            + "密码:   " + password + "\n"
                            + "生成于: " + LocalDateTime.now()
                            .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")) + "\n");
            System.out.println("[CONSOLE] First-run admin created. Credentials: " + f.toAbsolutePath());
        } catch (Exception e) {
            System.err.println("[CONSOLE] Could not write credential file: " + e.getMessage());
        }
    }

    public String login(String username, String password) {
        String hash = repo.findHash(username == null ? "" : username.trim());
        if (hash == null || !encoder.matches(password == null ? "" : password, hash)) return null;
        byte[] t = new byte[32];
        random.nextBytes(t);
        String token = Base64.getUrlEncoder().withoutPadding().encodeToString(t);
        sessions.put(token, new Session(username,
                System.currentTimeMillis() + props.getSessionTtl() * 1000));
        return token;
    }

    public String user(String token) {
        if (token == null) return null;
        Session s = sessions.get(token);
        if (s == null) return null;
        if (s.expiresAt() < System.currentTimeMillis()) { sessions.remove(token); return null; }
        return s.user();
    }

    public void logout(String token) { if (token != null) sessions.remove(token); }

    public Map<String, Object> changePassword(String user, String old, String next) {
        if (next == null || next.length() < 8)
            return Map.of("ok", false, "msg", "新密码至少 8 位");
        String hash = repo.findHash(user);
        if (hash == null || !encoder.matches(old == null ? "" : old, hash))
            return Map.of("ok", false, "msg", "原密码不正确");
        repo.updateHash(user, encoder.encode(next));
        return Map.of("ok", true, "msg", "密码已更新");
    }
}
