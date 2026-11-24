package com.signal.console.web;

import com.signal.console.model.Product;
import com.signal.console.service.CatalogService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/** Product administration: full CRUD incl. hidden items. */
@RestController
@RequestMapping("/api/admin/products")
public class ProductController {

    private final CatalogService catalog;

    public ProductController(CatalogService catalog) { this.catalog = catalog; }

    @GetMapping
    public Map<String, Object> list() {
        return Map.of("ok", true, "items", catalog.adminList());
    }

    @GetMapping("/{id}")
    public ResponseEntity<?> get(@PathVariable String id) {
        Product p = catalog.get(id);
        return p == null ? ResponseEntity.status(404).body(Map.of("ok", false, "msg", "商品不存在"))
                         : ResponseEntity.ok(Map.of("ok", true, "item", p));
    }

    @PostMapping
    public ResponseEntity<?> create(@RequestBody Product body) {
        Object r = catalog.save(body, null);
        if (r instanceof Map<?, ?> m && Boolean.FALSE.equals(m.get("ok")))
            return ResponseEntity.badRequest().body(r);
        return ResponseEntity.status(201).body(Map.of("ok", true, "item", r));
    }

    @PutMapping("/{id}")
    public ResponseEntity<?> update(@PathVariable String id, @RequestBody Product body) {
        if (catalog.get(id) == null)
            return ResponseEntity.status(404).body(Map.of("ok", false, "msg", "商品不存在"));
        Object r = catalog.save(body, id);
        if (r instanceof Map<?, ?> m && Boolean.FALSE.equals(m.get("ok")))
            return ResponseEntity.badRequest().body(r);
        return ResponseEntity.ok(Map.of("ok", true, "item", r));
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<?> delete(@PathVariable String id) {
        boolean ok = catalog.delete(id);
        return ResponseEntity.status(ok ? 200 : 404)
                .body(ok ? Map.of("ok", true) : Map.of("ok", false, "msg", "商品不存在"));
    }
}
