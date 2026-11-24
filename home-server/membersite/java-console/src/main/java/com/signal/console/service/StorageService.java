package com.signal.console.service;

import com.signal.console.config.ConsoleProperties;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.*;
import java.security.SecureRandom;
import java.util.*;

/** Base64 upload -> shared file store. Mirrors console.py StorageService. */
@Service
public class StorageService {

    private static final Set<String> ALLOWED = Set.of(
            ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico",
            ".pdf", ".md", ".txt", ".zip", ".csv", ".json",
            ".doc", ".docx", ".xls", ".xlsx");
    private static final long MAX = 10L * 1024 * 1024;
    private final Path dir;
    private final SecureRandom random = new SecureRandom();

    public StorageService(ConsoleProperties props) {
        this.dir = Paths.get(props.getUploadDir()).toAbsolutePath().normalize();
        try { Files.createDirectories(dir); } catch (IOException ignored) {}
    }

    public java.util.Map<String, Object> save(String filename, String dataB64) {
        String safe = (filename == null ? "upload.bin" : filename)
                .replaceAll("[^A-Za-z0-9._-]", "_");
        int dot = safe.lastIndexOf('.');
        String ext = dot >= 0 ? safe.substring(dot).toLowerCase() : "";
        if (!ALLOWED.contains(ext))
            return java.util.Map.of("ok", false, "msg", "不支持的文件类型：" + (ext.isEmpty() ? "未知" : ext));
        byte[] raw;
        try {
            String b64 = dataB64 == null ? "" : dataB64;
            int comma = b64.indexOf(',');
            raw = Base64.getDecoder().decode(comma >= 0 ? b64.substring(comma + 1) : b64);
        } catch (Exception e) {
            return java.util.Map.of("ok", false, "msg", "文件内容不是有效的 base64");
        }
        if (raw.length == 0 || raw.length > MAX)
            return java.util.Map.of("ok", false, "msg", "文件为空或超过 10 MB");
        byte[] n = new byte[10];
        random.nextBytes(n);
        String out = HexFormat.of().formatHex(n) + ext;
        try {
            Files.write(dir.resolve(out), raw, StandardOpenOption.CREATE_NEW);
        } catch (IOException e) {
            return java.util.Map.of("ok", false, "msg", "写入失败：" + e.getMessage());
        }
        return java.util.Map.of("ok", true, "url", "/uploads/" + out);
    }

    public List<java.util.Map<String, Object>> list() {
        List<java.util.Map<String, Object>> out = new ArrayList<>();
        try (var stream = Files.list(dir)) {
            stream.filter(Files::isRegularFile)
                    .sorted(Comparator.comparing(p -> p.getFileName().toString(), Comparator.reverseOrder()))
                    .limit(60)
                    .forEach(p -> {
                        try {
                            out.add(java.util.Map.of(
                                    "name", p.getFileName().toString(),
                                    "url", "/uploads/" + p.getFileName(),
                                    "size", Files.size(p)));
                        } catch (IOException ignored) {}
                    });
        } catch (IOException ignored) {}
        return out;
    }
}
