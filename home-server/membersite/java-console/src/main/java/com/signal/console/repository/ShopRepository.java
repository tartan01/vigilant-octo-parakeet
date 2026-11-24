package com.signal.console.repository;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.signal.console.model.Product;
import com.signal.console.model.ShopOrder;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * Repository — persistence only, no business rules.
 * Uses plain JDBC with EXACTLY the same table/column names as
 * membersite/store.py so both services can share one MySQL database.
 */
@Repository
public class ShopRepository {

    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper = new ObjectMapper();
    private static final DateTimeFormatter TS = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss");

    public ShopRepository(JdbcTemplate jdbc) { this.jdbc = jdbc; }

    private static String now() { return LocalDateTime.now().format(TS); }

    private List<String> jsonList(String s) {
        if (s == null || s.isBlank()) return new ArrayList<>();
        try { return mapper.readValue(s, new TypeReference<List<String>>() {}); }
        catch (Exception e) { return new ArrayList<>(); }
    }

    private List<Map<String, Object>> jsonMaps(String s) {
        if (s == null || s.isBlank()) return new ArrayList<>();
        try { return mapper.readValue(s, new TypeReference<List<Map<String, Object>>>() {}); }
        catch (Exception e) { return new ArrayList<>(); }
    }

    private String toJson(Object o) {
        try { return mapper.writeValueAsString(o == null ? Collections.emptyList() : o); }
        catch (Exception e) { return "[]"; }
    }

    // ---------------- Product RowMapper ----------------
    private final RowMapper<Product> PRODUCT_ROW = (rs, i) -> new Product(
            rs.getString("id"), rs.getString("name"), rs.getString("subtitle"),
            rs.getString("description"), rs.getDouble("price"),
            rs.getString("category"), rs.getString("cover"), rs.getString("badge"),
            rs.getInt("stock"), rs.getInt("hidden"), rs.getString("created_at"),
            rs.getString("format"), jsonList(rs.getString("delivery")),
            rs.getString("size"), rs.getString("author"), rs.getString("sample"),
            rs.getString("content"), rs.getString("file_url"),
            rs.getString("link_url"), rs.getString("link_code"),
            jsonList(rs.getString("code_pool")), rs.getString("email_template")
    );

    private final RowMapper<ShopOrder> ORDER_ROW = (rs, i) -> new ShopOrder(
            rs.getString("id"), rs.getString("email"), jsonMaps(rs.getString("items")),
            rs.getDouble("total"), rs.getString("status"), rs.getString("created_at"),
            rs.getString("delivery_method"), rs.getString("delivery_target"),
            jsonMaps(rs.getString("deliveries")), rs.getString("fulfilled_at")
    );

    // ---------------- Products ----------------
    public List<Product> listProducts(String category, String q, boolean includeHidden) {
        StringBuilder sql = new StringBuilder("SELECT * FROM products WHERE 1=1");
        List<Object> args = new ArrayList<>();
        if (!includeHidden) sql.append(" AND hidden = 0");
        if (category != null && !category.isBlank() && !"all".equals(category)) {
            sql.append(" AND category = ?"); args.add(category);
        }
        if (q != null && !q.isBlank()) {
            sql.append(" AND (LOWER(name) LIKE ? OR LOWER(subtitle) LIKE ? OR LOWER(description) LIKE ?)");
            String like = "%" + q.toLowerCase() + "%";
            args.add(like); args.add(like); args.add(like);
        }
        sql.append(" ORDER BY created_at ASC");
        return jdbc.query(sql.toString(), PRODUCT_ROW, args.toArray());
    }

    public Optional<Product> getProduct(String id) {
        List<Product> r = jdbc.query("SELECT * FROM products WHERE id = ?", PRODUCT_ROW, id);
        return r.stream().findFirst();
    }

    public Product saveProduct(Product p) {
        String id = (p.id() == null || p.id().isBlank())
                ? "d" + UUID.randomUUID().toString().substring(0, 8) : p.id();
        String created = (p.createdAt() == null || p.createdAt().isBlank()) ? now() : p.createdAt();
        List<String> delivery = p.delivery() == null || p.delivery().isEmpty()
                ? List.of("doc", "email", "online") : p.delivery();
        List<String> pool = p.codePool() == null ? new ArrayList<>() : p.codePool();
        int stock = p.stock() == null ? -1 : p.stock();
        int hidden = p.hidden() == null ? 0 : p.hidden();
        double price = p.price() == null ? 0 : p.price();

        if (getProduct(id).isPresent()) {
            jdbc.update("UPDATE products SET name=?, subtitle=?, description=?, price=?, " +
                            "category=?, cover=?, badge=?, stock=?, hidden=?, format=?, " +
                            "delivery=?, size=?, author=?, sample=?, content=?, file_url=?, " +
                            "link_url=?, link_code=?, code_pool=?, email_template=? WHERE id=?",
                    p.name(), p.subtitle(), p.description(), price, p.category(),
                    p.cover(), p.badge(), stock, hidden, p.format(), toJson(delivery),
                    p.size(), p.author(), p.sample(), p.content(), p.fileUrl(),
                    p.linkUrl(), p.linkCode(), toJson(pool), p.emailTemplate(), id);
        } else {
            jdbc.update("INSERT INTO products (id,name,subtitle,description,price,category," +
                            "cover,badge,stock,hidden,created_at,format,delivery,size,author," +
                            "sample,content,file_url,link_url,link_code,code_pool,email_template) " +
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    id, p.name(), p.subtitle(), p.description(), price, p.category(),
                    p.cover(), p.badge(), stock, hidden, created, p.format(), toJson(delivery),
                    p.size(), p.author(), p.sample(), p.content(), p.fileUrl(),
                    p.linkUrl(), p.linkCode(), toJson(pool), p.emailTemplate());
        }
        return getProduct(id).orElseThrow();
    }

    public boolean deleteProduct(String id) {
        return jdbc.update("DELETE FROM products WHERE id = ?", id) > 0;
    }

    /** Atomically pop one licence code from the pool. */
    public String takeCode(String id) {
        Product p = getProduct(id).orElse(null);
        if (p == null) return "SIG-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        List<String> pool = new ArrayList<>(p.codePool());
        String code = pool.isEmpty()
                ? "SIG-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase()
                : pool.remove(0);
        jdbc.update("UPDATE products SET code_pool = ? WHERE id = ?", toJson(pool), id);
        return code;
    }

    // ---------------- Orders ----------------
    public List<ShopOrder> listOrders(String email) {
        if (email == null || email.isBlank())
            return jdbc.query("SELECT * FROM orders ORDER BY created_at DESC", ORDER_ROW);
        return jdbc.query("SELECT * FROM orders WHERE email = ? ORDER BY created_at DESC", ORDER_ROW, email);
    }

    public Optional<ShopOrder> getOrder(String id) {
        return jdbc.query("SELECT * FROM orders WHERE id = ?", ORDER_ROW, id).stream().findFirst();
    }

    public ShopOrder saveOrder(ShopOrder o) {
        String id = (o.id() == null || o.id().isBlank())
                ? "ORD" + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"))
                  + "-" + UUID.randomUUID().toString().substring(0, 6).toUpperCase()
                : o.id();
        jdbc.update("INSERT INTO orders (id,email,items,total,status,created_at," +
                        "delivery_method,delivery_target,deliveries,fulfilled_at) " +
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                id, o.email(), toJson(o.items()), o.total(),
                o.status() == null ? "delivered" : o.status(),
                o.createdAt() == null ? now() : o.createdAt(),
                o.deliveryMethod(), o.deliveryTarget(), toJson(o.deliveries()),
                o.fulfilledAt() == null ? now() : o.fulfilledAt());
        return getOrder(id).orElseThrow();
    }

    public boolean updateOrderStatus(String id, String status, String note) {
        ShopOrder o = getOrder(id).orElse(null);
        if (o == null) return false;
        List<Map<String, Object>> deliveries = new ArrayList<>(o.deliveries());
        if (note != null && !note.isBlank()) {
            deliveries.add(Map.of("kind", "note", "text", note, "at", now()));
        }
        jdbc.update("UPDATE orders SET status = ?, deliveries = ? WHERE id = ?",
                status, toJson(deliveries), id);
        return true;
    }

    // ---------------- Counters ----------------
    public int countUsers()   { return jdbc.queryForObject("SELECT COUNT(*) FROM users", Integer.class); }
    public int countProducts(){ return jdbc.queryForObject("SELECT COUNT(*) FROM products", Integer.class); }
    public int countOrders()  { return jdbc.queryForObject("SELECT COUNT(*) FROM orders", Integer.class); }
    public double revenue()   { Double v = jdbc.queryForObject("SELECT COALESCE(SUM(total),0) FROM orders", Double.class); return v == null ? 0 : v; }
    public int pending()      { return jdbc.queryForObject("SELECT COUNT(*) FROM orders WHERE status <> 'delivered'", Integer.class); }
    public void clearProducts() { jdbc.update("DELETE FROM products"); }
}
