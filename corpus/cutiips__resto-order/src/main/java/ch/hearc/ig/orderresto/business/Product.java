package ch.hearc.ig.orderresto.business;

import java.math.BigDecimal;
import java.util.HashSet;
import java.util.Set;

public class Product {

    private Long id;
    private String name;
    private BigDecimal unitPrice;
    private String description;
    private Set<Order> orders;
    private Restaurant restaurant;

    public Product(Long id, String name, BigDecimal unitPrice, String description, Restaurant restaurant) {
        this.id = id;
        this.name = name;
        this.unitPrice = unitPrice;
        this.description = description;
        this.orders = new HashSet<>();
        this.restaurant = restaurant;
        if (restaurant != null) {
            restaurant.registerProduct(this); // Sert à ajouter le produit au restaurant
        }
    }

    public Long getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public BigDecimal getUnitPrice() {
        return unitPrice;
    }

    public String getDescription() {
        return description;
    }

    public Set<Order> getOrders() {
        return orders;
    }

    public Restaurant getRestaurant() {
        return restaurant;
    }

    @Override
    public String toString() {
        return String.format(
                "%s - %.2f de chez %s: %s",
                this.getName(),
                this.getUnitPrice(),
                this.getRestaurant().getName(),
                this.getDescription()
        );
    }

    public void addOrder(Order order) {
        this.orders.add(order);
    }

    public void setRestaurant(Restaurant restaurant) {
        this.restaurant = restaurant;
        if (restaurant != null) {
            restaurant.registerProduct(this);
        }
    }

    public void setId(Long id) {
        if (this.id == null) {
            this.id = id;
        }
    }

    public void setName(String name) {
        this.name = name;
    }

    public void setUnitPrice (BigDecimal unitPrice) {
        this.unitPrice = unitPrice;
    }

}