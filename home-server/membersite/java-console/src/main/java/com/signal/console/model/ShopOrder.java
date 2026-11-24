package com.signal.console.model;

import java.util.List;
import java.util.Map;

/** Order record. ``items`` and ``deliveries`` are JSON in the database. */
public record ShopOrder(
        String id,
        String email,
        List<Map<String, Object>> items,
        Double total,
        String status,
        String createdAt,
        String deliveryMethod,
        String deliveryTarget,
        List<Map<String, Object>> deliveries,
        String fulfilledAt
) {}
