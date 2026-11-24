package com.signal.console.web;

import com.signal.console.repository.ShopRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** Order administration: list all orders, mark delivered / pending, append notes. */
@RestController
@RequestMapping("/api/admin/orders")
public class OrderController {

    private final ShopRepository repo;

    public OrderController(ShopRepository repo) { this.repo = repo; }

    @GetMapping
    public Map<String, Object> list() {
        return Map.of("ok", true, "items", (java.util.List<?>) repo.listOrders(null));
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> update(@PathVariable String id,
                                    @RequestBody(required = false) Map<String, String> body) {
        Map<String, String> b = body == null ? Map.of() : body;
        String status = b.getOrDefault("status", "delivered");
        boolean ok = repo.updateOrderStatus(id, status, b.get("note"));
        if (!ok) return ResponseEntity.status(404).body(Map.of("ok", false, "msg", "订单不存在"));
        return ResponseEntity.ok(Map.of("ok", true, "order", repo.getOrder(id).orElseThrow()));
    }
}
