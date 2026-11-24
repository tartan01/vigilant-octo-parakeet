package com.signal.console.web;

import com.signal.console.model.Product;
import com.signal.console.repository.ShopRepository;
import com.signal.console.service.CatalogService;
import com.signal.console.service.FulfillmentService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Read-only storefront endpoints. Same paths/payloads as membersite/server.py,
 * so the Apple-style front end works unchanged against either backend.
 */
@RestController
public class PublicController {

    private final ShopRepository repo;
    private final CatalogService catalog;
    private final FulfillmentService fulfilment;

    public PublicController(ShopRepository repo, CatalogService catalog,
                            FulfillmentService fulfilment) {
        this.repo = repo; this.catalog = catalog; this.fulfilment = fulfilment;
    }

    @GetMapping("/api/status")
    public Map<String, Object> status() {
        return Map.of("ok", true, "service", "signal-console-java",
                "time", LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME),
                "backend", "jdbc", "users", repo.countUsers(),
                "products", repo.countProducts(), "orders", repo.countOrders());
    }

    @GetMapping("/api/products")
    public Map<String, Object> products(@RequestParam(required = false) String category,
                                        @RequestParam(required = false) String q) {
        var items = catalog.publicList(category, q);
        return Map.of("ok", true, "items", items, "total", items.size());
    }

    @GetMapping("/api/products/{id}")
    public ResponseEntity<?> product(@PathVariable String id) {
        Product p = catalog.get(id);
        if (p == null) return ResponseEntity.status(404).body(Map.of("ok", false, "msg", "商品不存在"));
        return ResponseEntity.ok(Map.of("ok", true, "item", p.publicView()));
    }

    @GetMapping("/api/delivery-methods")
    public Map<String, Object> deliveryMethods() {
        return Map.of("ok", true, "items", List.of(
                Map.of("key", "doc", "name", "文档发货", "en", "Document", "desc", "付款后立即生成下载链接，PDF / Markdown / ZIP 直接到手。"),
                Map.of("key", "email", "name", "邮件发货", "en", "Email", "desc", "把文件与说明发到你指定的邮箱，留档可查。"),
                Map.of("key", "link", "name", "私密外链", "en", "Private link", "desc", "交付私密链接与提取码，适合网盘与在线文档。"),
                Map.of("key", "code", "name", "授权码", "en", "Licence code", "desc", "即时发放一次性授权码 / 卡密，用于开通订阅或软件。"),
                Map.of("key", "online", "name", "站内查阅", "en", "Read online", "desc", "无需下载，在「我的订单」里直接阅读全文，随时回看。")));
    }

    @GetMapping("/api/brief")
    public Map<String, Object> brief() {
        return Map.of("ok", true, "brief", Map.of(
                "title", "金融科技信息简报 · 第 01 期",
                "lead", "把噪声折叠起来，只留下能改变判断的那几条。",
                "sourcesLabel", "信息源分享",
                "sources", List.of(
                        "一手源优先：监管公告、交易所披露、发行人文件。",
                        "为每个源标注更新频率 / 口径 / 滞后。",
                        "建一份可回溯清单：来源、时间、校验人。"),
                "aiLabel", "AI 信息分享",
                "ai", List.of(
                        "让模型做抽取与对齐，不让它做结论。",
                        "每条输出都带原文出处；无出处，即丢弃。",
                        "提示词与版本入库，结果才可复现。"),
                "foot", "信息差不在更多，而在更快被验证。"));
    }

    /** Demo order creation. In production, guard this with a member session. */
    @PostMapping("/api/orders")
    public ResponseEntity<?> orders(@RequestBody Map<String, Object> body) {
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> lines = (List<Map<String, Object>>) body.get("items");
        String email = String.valueOf(body.getOrDefault("email", "demo@signal.local"));
        String method = String.valueOf(body.getOrDefault("deliveryMethod", "doc"));
        String target = String.valueOf(body.getOrDefault("deliveryTarget", ""));
        try {
            var o = fulfilment.createOrder(email, lines, method, target);
            return ResponseEntity.status(201).body(Map.of("ok", true, "order", o));
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().body(Map.of("ok", false, "msg", e.getMessage()));
        }
    }

    @GetMapping("/api/download")
    public ResponseEntity<byte[]> download(@RequestParam String order, @RequestParam String item) {
        var o = repo.getOrder(order);
        if (o.isEmpty()) return ResponseEntity.status(403).build();
        boolean allowed = o.get().deliveries().stream()
                .anyMatch(d -> item.equals(d.get("itemId")) && "doc".equals(d.get("kind")));
        if (!allowed) return ResponseEntity.status(403).build();
        Product p = repo.getProduct(item).orElse(null);
        String text = "# " + (p == null ? item : p.name()) + "\n\n"
                + (p == null || p.content() == null ? "" : p.content())
                + "\n\n---\n本文件由 SIGNAL Java Console 生成，仅限购买者本人使用。\n";
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + item + ".md\"")
                .contentType(MediaType.parseMediaType("text/markdown; charset=UTF-8"))
                .body(text.getBytes(StandardCharsets.UTF_8));
    }
}
