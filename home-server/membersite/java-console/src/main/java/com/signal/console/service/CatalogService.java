package com.signal.console.service;

import com.signal.console.model.Product;
import com.signal.console.repository.ShopRepository;
import org.springframework.stereotype.Service;

import java.util.List;

/** Business rules for the catalogue. Public reads are always sanitised. */
@Service
public class CatalogService {

    private static final List<String> METHODS = List.of("doc", "email", "link", "code", "online");
    private final ShopRepository repo;

    public CatalogService(ShopRepository repo) { this.repo = repo; }

    /** Admin context: FULL record, so editing does not wipe fulfilment fields. */
    public List<Product> adminList() {
        return repo.listProducts(null, null, true);
    }

    public List<Product.PublicView> publicList(String category, String q) {
        return repo.listProducts(category, q, false).stream().map(Product::publicView).toList();
    }

    public Product get(String id) { return repo.getProduct(id).orElse(null); }

    public Object save(Product in, String id) {
        if (in.name() == null || in.name().isBlank())
            return java.util.Map.of("ok", false, "msg", "商品名称不能为空");
        List<String> methods = in.delivery() == null ? List.of() : in.delivery().stream()
                .filter(METHODS::contains).distinct().toList();
        if (methods.isEmpty())
            return java.util.Map.of("ok", false, "msg", "至少选择一种发货方式");

        String useId = (id != null && !id.isBlank()) ? id : in.id();
        Product normalised = new Product(
                useId, in.name().trim(), in.subtitle(), in.description(),
                in.price() == null ? 0.0 : in.price(), in.category(),
                in.cover(), in.badge(), in.stock() == null ? -1 : in.stock(),
                in.hidden() == null ? 0 : in.hidden(), in.createdAt(), in.format(),
                methods, in.size(), in.author(), in.sample(), in.content(),
                in.fileUrl(), in.linkUrl(), in.linkCode(),
                in.codePool() == null ? List.of() : in.codePool(), in.emailTemplate());
        return repo.saveProduct(normalised);
    }

    public boolean delete(String id) { return repo.deleteProduct(id); }

    public java.util.Map<String, Object> overview() {
        var orders = repo.listOrders(null);
        return java.util.Map.of(
                "users", repo.countUsers(), "products", repo.countProducts(),
                "orders", orders.size(), "revenue", repo.revenue(),
                "pending", repo.pending(),
                "recentOrders", orders.stream().limit(5).toList());
    }
}
