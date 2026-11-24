package com.signal.console.web;

import com.signal.console.service.AuthService;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.io.IOException;

/** Session guard for /api/admin/** (login & session are excluded in WebConfig). */
@Component
public class AdminInterceptor implements HandlerInterceptor {

    public static final String COOKIE = "csid";
    private final AuthService auth;

    public AdminInterceptor(AuthService auth) { this.auth = auth; }

    @Override
    public boolean preHandle(HttpServletRequest req, HttpServletResponse res, Object handler)
            throws IOException {
        if ("OPTIONS".equalsIgnoreCase(req.getMethod())) return true;
        String token = readCookie(req, COOKIE);
        if (auth.user(token) != null) return true;
        res.setStatus(401);
        res.setContentType("application/json;charset=UTF-8");
        res.getWriter().write("{\"ok\":false,\"msg\":\"后台会话已失效，请重新登录\"}");
        return false;
    }

    public static String readCookie(HttpServletRequest req, String name) {
        Cookie[] cookies = req.getCookies();
        if (cookies == null) return null;
        for (Cookie c : cookies) if (name.equals(c.getName())) return c.getValue();
        return null;
    }
}
