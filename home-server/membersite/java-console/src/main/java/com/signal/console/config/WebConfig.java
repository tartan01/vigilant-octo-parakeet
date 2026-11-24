package com.signal.console.config;

import com.signal.console.web.AdminInterceptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.*;

import java.nio.file.Path;

@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Autowired
    private AdminInterceptor adminInterceptor;

    @Autowired
    private ConsoleProperties props;

    /** Serve uploaded files from the shared directory at /uploads/**. */
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        Path dir = java.nio.file.Paths.get(props.getUploadDir())
                .toAbsolutePath().normalize();
        try { java.nio.file.Files.createDirectories(dir); } catch (Exception ignored) {}
        String location = dir.toUri().toString();
        if (!location.endsWith("/")) location += "/";
        registry.addResourceHandler("/uploads/**").addResourceLocations(location);
    }

    /** Every /api/admin/* endpoint except login/session requires a valid session. */
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(adminInterceptor)
                .addPathPatterns("/api/admin/**")
                .excludePathPatterns("/api/admin/login", "/api/admin/session");
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("Content-Type")
                .allowCredentials(true);
    }
}
