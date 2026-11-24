package com.signal.console.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "signal.console")
public class ConsoleProperties {
    /** Upload directory, shared with the Python storefront's /uploads/* path. */
    private String uploadDir = "../uploads";
    /** Admin session lifetime in seconds. */
    private long sessionTtl = 28800;
    /** Bootstrap administrator username. */
    private String bootstrapUser = "admin";

    public String getUploadDir() { return uploadDir; }
    public void setUploadDir(String uploadDir) { this.uploadDir = uploadDir; }
    public long getSessionTtl() { return sessionTtl; }
    public void setSessionTtl(long sessionTtl) { this.sessionTtl = sessionTtl; }
    public String getBootstrapUser() { return bootstrapUser; }
    public void setBootstrapUser(String bootstrapUser) { this.bootstrapUser = bootstrapUser; }
}
