package com.signal.console.service;

import com.signal.console.model.Product;
import com.signal.console.model.ShopOrder;
import com.signal.console.repository.ShopRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Fulfilment rules — the Java twin of server.py::build_deliveries.
 * Five delivery modes, with automatic fallback when an item lacks the chosen one.
 */
@Service
public class FulfillmentService {

    private static final Map<String, String> NAMES = Map.of(
            "doc", "文档发货", "email", "邮件发货", "link", "私密外链",
            "code", "授权码", "online", "站内查阅");
    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");
    private final ShopRepository repo;

    public FulfillmentService(ShopRepository repo) { this.repo = repo; }

    public ShopOrder createOrder(String email, List<Map<String, Object>> lines,
                                 String method, String target) {
        if (lines == null || lines.isEmpty()) throw new IllegalArgumentException("购物车是空的");
        String useMethod = NAMES.containsKey(method) ? method : "doc";
        String useTarget = (target == null || target.isBlank()) ? email : target;

        double total = 0;
        List<Map<String, Object>> items = new ArrayList<>();
        Map<String, Product> lookup = new HashMap<>();
        for (Map<String, Object> line : lines) {
            String pid = String.valueOf(line.get("id"));
            Product p = repo.getProduct(pid).orElseThrow(() -> new IllegalArgumentException("商品 " + pid + " 已下架"));
            if (p.hidden() != null && p.hidden() == 1) throw new IllegalArgumentException("商品 " + pid + " 已下架");
            int qty = Math.max(1, Math.min(99, ((Number) line.getOrDefault("qty", 1)).intValue()));
            if (p.stock() != null && p.stock() != -1 && p.stock() < qty)
                throw new IllegalArgumentException("「" + p.name() + "」库存不足");
            double sub = p.price() * qty;
            total += sub;
            Map<String, Object> it = new LinkedHashMap<>();
            it.put("id", pid); it.put("name", p.name()); it.put("price", p.price());
            it.put("qty", qty); it.put("subtotal", Math.round(sub * 100.0) / 100.0);
            items.add(it);
            lookup.put(pid, p);
        }

        String id = "ORD" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"))
                + "-" + UUID.randomUUID().toString().substring(0, 6).toUpperCase();
        List<Map<String, Object>> deliveries = buildDeliveries(id, items, useMethod, useTarget, lookup);
        return repo.saveOrder(new ShopOrder(id, email, items,
                Math.round(total * 100.0) / 100.0, "delivered",
                LocalDateTime.now().format(TS), useMethod, useTarget, deliveries,
                LocalDateTime.now().format(TS)));
    }

    private List<Map<String, Object>> buildDeliveries(String orderId,
            List<Map<String, Object>> items, String method, String target,
            Map<String, Product> lookup) {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Map<String, Object> it : items) {
            String pid = String.valueOf(it.get("id"));
            Product p = lookup.get(pid);
            List<String> enabled = (p.delivery() == null || p.delivery().isEmpty())
                    ? List.of("doc") : p.delivery();
            String actual = enabled.contains(method) ? method : enabled.get(0);
            Map<String, Object> d = new LinkedHashMap<>();
            d.put("itemId", pid); d.put("name", p.name());
            d.put("method", actual); d.put("methodName", NAMES.get(actual));
            if (!actual.equals(method)) d.put("fallback", true);
            d.put("kind", actual);
            switch (actual) {
                case "doc" -> {
                    d.put("fileName", safe(p.name()) + ".md");
                    d.put("url", "/api/download?order=" + orderId + "&item=" + pid);
                    d.put("note", "点击下载，链接仅对你本人有效。");
                }
                case "email" -> {
                    d.put("to", target);
                    d.put("subject", "【SIGNAL】你的数字文件已送达 · " + p.name());
                    d.put("status", "queued");
                    d.put("note", "已排入邮件队列（演示模式，接入邮件服务后自动发送）。");
                    d.put("preview", p.content() == null ? p.sample() : p.content());
                }
                case "link" -> {
                    d.put("url", p.linkUrl() == null ? "" : p.linkUrl());
                    d.put("code", p.linkCode() == null ? "" : p.linkCode());
                    d.put("note", "私密链接与提取码，请勿公开分享。");
                }
                case "code" -> {
                    d.put("code", repo.takeCode(pid));
                    d.put("note", "一次性授权码，请妥善保存。");
                }
                case "online" -> {
                    d.put("content", p.content() == null ? "" : p.content());
                    d.put("note", "全文已解锁，可随时回来查阅。");
                }
                default -> d.put("note", "");
            }
            out.add(d);
        }
        return out;
    }

    private static String safe(String s) {
        return (s == null ? "file" : s).replaceAll("[^0-9A-Za-z\\u4e00-\\u9fff._-]", "_");
    }
}
