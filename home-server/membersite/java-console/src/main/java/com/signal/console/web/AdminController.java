package com.signal.console.web;

import com.signal.console.service.AuthService;
import com.signal.console.service.CatalogService;
import com.signal.console.service.StorageService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** Auth + dashboard + uploads. Endpoint paths match the Python service exactly. */
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private final AuthService auth;
    private final CatalogService catalog;
    private final StorageService storage;

    public AdminController(AuthService auth, CatalogService catalog, StorageService storage) {
        this.auth = auth; this.catalog = catalog; this.storage = storage;
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@RequestBody Map<String, String> body, HttpServletResponse res) {
        String token = auth.login(body.get("username"), body.get("password"));
        if (token == null)
            return ResponseEntity.status(401).body(Map.of("ok", false, "msg", "账号或密码不正确"));
        Cookie c = new Cookie(AdminInterceptor.COOKIE, token);
        c.setHttpOnly(true); c.setPath("/"); c.setMaxAge(28800);
        res.addCookie(c);
        return ResponseEntity.ok(Map.of("ok", true, "user", body.get("username")));
    }

    @PostMapping("/logout")
    public Map<String, Object> logout(HttpServletRequest req, HttpServletResponse res) {
        auth.logout(AdminInterceptor.readCookie(req, AdminInterceptor.COOKIE));
        Cookie c = new Cookie(AdminInterceptor.COOKIE, "");
        c.setHttpOnly(true); c.setPath("/"); c.setMaxAge(0);
        res.addCookie(c);
        return Map.of("ok", true);
    }

    @GetMapping("/session")
    public Map<String, Object> session(HttpServletRequest req) {
        String u = auth.user(AdminInterceptor.readCookie(req, AdminInterceptor.COOKIE));
        return Map.of("ok", true, "loggedIn", u != null, "user", u == null ? "" : u);
    }

    @PostMapping("/password")
    public Map<String, Object> password(HttpServletRequest req, @RequestBody Map<String, String> b) {
        String u = auth.user(AdminInterceptor.readCookie(req, AdminInterceptor.COOKIE));
        return auth.changePassword(u, b.get("old"), b.get("new"));
    }

    @GetMapping("/overview")
    public Map<String, Object> overview() { return catalog.overview(); }

    @PostMapping("/upload")
    public ResponseEntity<?> upload(@RequestBody Map<String, String> b) {
        Map<String, Object> r = storage.save(b.get("filename"), b.get("data"));
        return ResponseEntity.status(Boolean.TRUE.equals(r.get("ok")) ? 201 : 400).body(r);
    }

    @GetMapping("/uploads")
    public Map<String, Object> uploads() {
        return Map.of("ok", true, "items", (List<?>) storage.list());
    }
}
