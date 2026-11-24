package com.signal.console.model;

import java.util.List;

/**
 * Digital-goods product. Field names are camelCase to match the storefront JSON
 * contract exactly; the Repository maps them to snake_case SQL columns.
 */
public record Product(
        String id,
        String name,
        String subtitle,
        String description,
        Double price,
        String category,
        String cover,
        String badge,
        Integer stock,
        Integer hidden,
        String createdAt,
        String format,
        List<String> delivery,
        String size,
        String author,
        String sample,
        String content,
        String fileUrl,
        String linkUrl,
        String linkCode,
        List<String> codePool,
        String emailTemplate
) {
    /** Only these fields may be returned by a PUBLIC endpoint. */
    public record PublicView(
            String id, String name, String subtitle, String description,
            Double price, String category, String cover, String badge,
            Integer stock, Integer hidden, String createdAt, String format,
            List<String> delivery, String size, String author, String sample) {}

    public PublicView publicView() {
        return new PublicView(id, name, subtitle, description, price, category,
                cover, badge, stock, hidden, createdAt, format, delivery, size,
                author, sample);
    }
}
