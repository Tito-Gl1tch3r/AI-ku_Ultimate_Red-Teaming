package ch.hearc.ig.orderresto.presentation.cli;

import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.business.Order;
import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.presentation.AbstractCLI;
import ch.hearc.ig.orderresto.service.OrderService;
import ch.hearc.ig.orderresto.service.exceptions.CustomerServiceException;

import java.sql.SQLException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class OrderCLI extends AbstractCLI {
    private final OrderService orderService = new OrderService();


    public Order createNewOrder() throws SQLException, RestaurantPersistenceException, CustomerPersistenceException, ProductPersistenceException, CustomerServiceException {
        MainCLI mainCLI = new MainCLI();
        this.ln("======================================================");
        Restaurant restaurant = (new RestaurantCLI()).displayRestaurantIdsAndNames(false);

        Set<Long> insertedProducts = new HashSet<>(); //TEST


        ProductCLI productCLI = new ProductCLI();
        Order order = new Order(null, null, restaurant, false, LocalDateTime.now());
        while (true) {
            Product selectedProduct = productCLI.displayProductsForRestaurant(restaurant);
            if (insertedProducts.contains(selectedProduct.getId())) {
                this.ln("Ce produit a déjà été ajouté à la commande.");
                this.ln("Ajouter un autre produit ? (1: Oui, 0: Non)");
                int addMore = this.readIntFromUser(1);
                if (addMore == 0) break;
            } else {
                order.addProduct(selectedProduct);
                insertedProducts.add(selectedProduct.getId());
                this.ln("Produit ajouté : " + selectedProduct.getName());
                this.ln("Ajouter un autre produit ? (1: Oui, 0: Non)");
                int addMore = this.readIntFromUser(1);
                if (addMore == 0) break;
            }

//            if (selectedProduct != null) {
//                order.addProduct(selectedProduct);
//                this.ln("Produit ajouté : " + selectedProduct.getName());
//                this.ln("Ajouter un autre produit ? (1: Oui, 0: Non)");
//                int addMore = this.readIntFromUser(1);
//                if (addMore == 0) break;
//            } else {
//                mainCLI.run();
//            }


        }

        // Choix du type de commande
        this.ln("Commande à emporter ? (1: Oui, 0: Non)");
        boolean takeAway = this.readIntFromUser(1) == 1;
        order.setTakeAway(takeAway);


        this.ln("======================================================");
        this.ln("0. Annuler");
        this.ln("1. Je suis un client existant");
        this.ln("2. Je suis un nouveau client");

        int userChoice = this.readIntFromUser(2);
        if (userChoice == 0) {
            mainCLI.run();
            return null;
        }

        CustomerCLI customerCLI = new CustomerCLI();
        Customer customer;
        if (userChoice == 1) {
            customer = customerCLI.getExistingCustomer();
        } else {
            customer = customerCLI.addCustomer();
        }

        if (customer == null) {
            this.ln("Erreur : Impossible de récupérer ou de créer le client. Commande annulée.");
            return null;
        }

        // Possible improvements:
        // - ask whether it's a takeAway order or not?
        // - Ask user for multiple products?
        order.setCustomer(customer);

        // Insertion de la commande en base de données via OrderService
        boolean success = false;
        try {
            success = orderService.createOrder(order);
        } catch (ch.hearc.ig.orderresto.service.exceptions.OrderServiceException e) {
            throw new RuntimeException(e);
        }
        if (success) {
            this.ln("Commande passée avec succès ! Merci pour votre commande.");
        } else {
            this.ln("Erreur lors de la création de la commande. Veuillez réessayer.");
        }


        return order;
    }

    public Order selectOrder() throws SQLException, CustomerServiceException, RestaurantPersistenceException, CustomerPersistenceException, ProductPersistenceException {
        Customer customer = (new CustomerCLI()).getExistingCustomer();
        List<Order> orders;
        try {
            orders = orderService.findOrdersByCustomer(customer);
        } catch (ch.hearc.ig.orderresto.service.exceptions.OrderServiceException e) {
            throw new RuntimeException(e);
        }

        if (orders.isEmpty()) {
            this.ln(String.format("Désolé, il n'y a aucune commande pour %s", customer.getEmail()));
            return null;
        }

        this.ln("Choisissez une commande:");
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("dd.MM.yyyy à hh:mm");
        for (int i = 0; i < orders.size(); i++) {
            Order order = orders.get(i);
            LocalDateTime when = order.getWhen();
            this.ln(String.format("%d. %.2f CHF, le %s chez %s.", i, order.getTotalAmount(), when.format(formatter), order.getRestaurant().getName()));
        }
        int index = this.readIntFromUser(orders.size() - 1);
        return orders.get(index);
    }

    public void displayOrder(Order order) {
        if (order == null) {
            this.ln("Commande non trouvée.");
            return;
        }

        LocalDateTime when = order.getWhen();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("dd.MM.yyyy à hh:mm");
        this.ln(String.format("Commande de %.2f CHF, le %s chez %s :",
                order.getTotalAmount(), when.format(formatter), order.getRestaurant().getName()));

        int index = 1;
        for (Product product : order.getProducts()) {
            this.ln(String.format("%d. %s - %.2f CHF", index, product.getName(), product.getUnitPrice()));
            index++;
        }

        this.ln("À emporter : " + (order.getTakeAway() ? "Oui" : "Non"));
    }
}
