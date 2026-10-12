package ch.hearc.ig.orderresto.presentation.cli;

import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.business.Product;
import ch.hearc.ig.orderresto.business.Restaurant;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.presentation.AbstractCLI;
import ch.hearc.ig.orderresto.service.ProductService;
import ch.hearc.ig.orderresto.service.RestaurantService;
import ch.hearc.ig.orderresto.service.exceptions.ProductServiceException;

import java.sql.SQLException;
import java.util.List;

/**
 * 🚀 Gère les interactions CLI pour les opérations CRUD des restaurants.
 * Permet d'ajouter, consulter, mettre à jour, supprimer et afficher les restaurants.
 */
public class RestaurantCLI extends AbstractCLI {
    private final RestaurantService restaurantService = new RestaurantService();

    /**
     * 🎛️ Démarre le menu de gestion des restaurants.
     * Affiche les options et permet à l'utilisateur de sélectionner une action.
     */
    public void run() throws SQLException, RestaurantPersistenceException {
        this.ln("======================================================");
        this.ln("Gestion des restaurants");
        this.ln("0. Retour au menu principal");
        this.ln("1. Ajouter un nouveau restaurant");
        this.ln("2. Consulter un restaurant existant");
        this.ln("3. Mettre à jour un restaurant");
        this.ln("4. Supprimer un restaurant");
        this.ln("5. Voir tous les restaurants");
        int userChoice = this.readIntFromUser(5);
        this.handleUserChoice(userChoice);
    }

    /**
     * 🎯 Gère le choix de l'utilisateur pour le menu des restaurants.
     * Exécute l'action correspondante en fonction du choix.
     * @param userChoice Choix de l'utilisateur (de 0 à 5).
     */
    private void handleUserChoice(int userChoice) throws SQLException, RestaurantPersistenceException {
        switch (userChoice) {
            case 0:
                return;
            case 1:
                addRestaurant();
                break;
            case 2:
                displayRestaurantIdsAndNames(true);
                break;
            case 3:
                updateRestaurant();
                break;
            case 4:
                deleteRestaurant();
                break;
            case 5:
                displayAllRestaurants();
                break;
            default:
                this.ln("Choix non valide, veuillez réessayer.");
        }
        this.run();
    }

    /**
     * ➕ Ajoute un nouveau restaurant avec son adresse.
     * Demande les informations du restaurant à l'utilisateur.
     */
    private void addRestaurant() {
        this.ln("Ajouter un nouveau restaurant - nom du restaurant : ");
        String name = this.readStringFromUser();

        Address address = readAddressFromUser();

        Restaurant restaurant = new Restaurant(null, name, address);

        try {
            restaurantService.addRestaurant(restaurant);
        } catch (ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 🔄 Met à jour un restaurant existant.
     * Demande l'ID du restaurant à mettre à jour, puis les nouvelles informations.
     * Si une entrée est vide, conserve l'ancienne valeur.
     */
    private void updateRestaurant() throws SQLException, RestaurantPersistenceException {
        this.ln("Voici la liste des restaurants (ID et Nom) :");
        this.displayAllRestaurants();

        this.ln("Entrez l'ID du restaurant à mettre à jour : ");
        Long id = this.readLongFromUser();
        try {
            Restaurant existingRestaurant = restaurantService.getRestaurantById(id);
            if (existingRestaurant == null) {
                this.ln("Restaurant non trouvé.");
                return;
            }

            this.ln("Nouveau nom (actuel : " + existingRestaurant.getName() + ", appuyez sur Entrée pour garder inchangé) : ");
            String newName = this.readStringFromUserAllowEmpty();
            if (newName == null || newName.isEmpty()) {
                newName = existingRestaurant.getName();
            }

            this.ln("Nouveau code postal (actuel : " + existingRestaurant.getAddress().getPostalCode() + ", appuyez sur Entrée pour garder inchangé) : ");
            String newPostalCode = this.readStringFromUserAllowEmpty();
            if (newPostalCode.isEmpty()) {
                newPostalCode = existingRestaurant.getAddress().getPostalCode();
            }

            this.ln("Nouveau code pays (actuel : " + existingRestaurant.getAddress().getCountryCode() + ", appuyez sur Entrée pour garder inchangé) : ");
            String newCountryCode = this.readStringFromUserAllowEmpty();
            if (newCountryCode.isEmpty()) {
                newCountryCode = existingRestaurant.getAddress().getCountryCode();
            }

            this.ln("Nouvelle localité (actuel : " + existingRestaurant.getAddress().getLocality() + ", appuyez sur Entrée pour garder inchangé) : ");
            String newLocality = this.readStringFromUserAllowEmpty();
            if (newLocality.isEmpty()) {
                newLocality = existingRestaurant.getAddress().getLocality();
            }

            this.ln("Nouvelle rue (actuel : " + existingRestaurant.getAddress().getStreet() + ", appuyez sur Entrée pour garder inchangé) : ");
            String newStreet = this.readStringFromUserAllowEmpty();
            if (newStreet.isEmpty()) {
                newStreet = existingRestaurant.getAddress().getStreet();
            }

            this.ln("Nouveau numéro de rue (actuel : " + existingRestaurant.getAddress().getStreetNumber() + ", appuyez sur Entrée pour garder inchangé) : ");
            String newStreetNumber = this.readStringFromUserAllowEmpty();
            if (newStreetNumber.isEmpty()) {
                newStreetNumber = existingRestaurant.getAddress().getStreetNumber();
            }

            Address updatedAddress = new Address(
                    newCountryCode,
                    newPostalCode,
                    newLocality,
                    newStreet,
                    newStreetNumber
            );
            Restaurant updatedRestaurant = new Restaurant(id, newName, updatedAddress);
            restaurantService.updateRestaurant(updatedRestaurant);

            manageRestaurantProducts(updatedRestaurant);
            this.ln("Restaurant mis à jour avec succès !");

        } catch (SQLException | ProductPersistenceException e) {
            this.ln("Erreur lors de la mise à jour du restaurant : " + e.getMessage());
        } catch (ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException e) {
            throw new RuntimeException(e);
        }
    }

    private void manageRestaurantProducts(Restaurant restaurant) throws SQLException, ProductPersistenceException {
        ProductCLI productCLI = new ProductCLI();

        while (true) {
            this.ln("\nGestion des produits pour le restaurant " + restaurant.getName());
            this.ln("1. Ajouter un nouveau produit");
            this.ln("2. Mettre à jour un produit existant");
            this.ln("3. Supprimer un produit");
            this.ln("0. Retourner");

            int choice = this.readIntFromUser(3);

            switch (choice) {
                case 1:
                    productCLI.addProduct(restaurant);
                    break;
                case 2:
                    productCLI.updateProduct(restaurant);
                    break;
                case 3:
                    productCLI.deleteProduct();
                    break;
                case 0:
                    return; // Quitte le menu de gestion des produits
                default:
                    this.ln("Choix non valide, veuillez réessayer.");
            }
        }
    }

    /**
     * 🗑️ Supprime un restaurant par son ID.
     * Affiche la liste des restaurants avec leurs ID pour que l'utilisateur puisse choisir.
     */
    private void deleteRestaurant() throws SQLException, RestaurantPersistenceException {
        this.ln("Voici la liste des restaurants (ID et Nom) :");
        this.displayAllRestaurants();

        this.ln("Entrez l'ID du restaurant à supprimer : ");
        Long id = this.readLongFromUser();
        try {
            restaurantService.deleteRestaurant(id);
        } catch (ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException e) {
            throw new RuntimeException(e);
        }
        this.ln("Restaurant supprimé avec succès !");
    }

    /**
     * 📋 Affiche la liste complète des restaurants avec leurs informations.
     * Utilise la méthode displayRestaurant pour afficher chaque restaurant.
     */
    private void displayAllRestaurants() {
        List<Restaurant> restaurants = null;
        try {
            restaurants = restaurantService.getAllRestaurants();
        } catch (ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException e) {
            throw new RuntimeException(e);
        }
        if (restaurants.isEmpty()) {
            this.ln("Aucun restaurant trouvé.");
        } else {
            for (Restaurant restaurant : restaurants) {
                displayRestaurant(restaurant, false);
            }
        }
    }

    /**
     * 📄 Affiche uniquement les IDs et les noms des restaurants.
     * Utile pour la mise à jour ou la suppression des restaurants.
     */
    public Restaurant displayRestaurantIdsAndNames(boolean displayProducts) throws RestaurantPersistenceException {
        this.ln("Choisissez un restaurant:");
        List<Restaurant> allRestaurants = null;
        try {
            allRestaurants = restaurantService.getAllRestaurants();
        } catch (ch.hearc.ig.orderresto.service.exceptions.RestaurantServiceException e) {
            throw new RuntimeException(e);
        }
        for (int i = 0 ; i < allRestaurants.size() ; i++) {
            Restaurant restaurant = allRestaurants.get(i);
            this.ln(String.format("%d. ID: %d - Nom: %s.", i, restaurant.getId(), restaurant.getName()));
        }
        int index = this.readIntFromUser(allRestaurants.size() - 1);
        this.displayRestaurant(allRestaurants.get(index), displayProducts);
        return (Restaurant) allRestaurants.get(index);
    }

    /**
     * 📝 Affiche les détails complets d'un restaurant.
     * @param restaurant Le restaurant a affiché.
     */
    private void displayRestaurant(Restaurant restaurant, boolean displayProducts) {
        this.ln(String.format("ID: %s, Nom: %s, Adresse: %s %s, %s %s",
                restaurant.getId(),
                restaurant.getName(),
                restaurant.getAddress().getStreet(),
                restaurant.getAddress().getStreetNumber(),
                restaurant.getAddress().getPostalCode(),
                restaurant.getAddress().getLocality()));
        if (displayProducts) {
            // demandez à l'utilisateur s'il souhaite afficher les produits du restaurant
            this.ln("Voulez-vous afficher les produits de ce restaurant ? [oui / non]");
            boolean choice = this.readBooleanFromUser();
            if (choice) {
                ProductService productService = new ProductService();
                ProductCLI productCLI = new ProductCLI();
                try {
                    List<Product> products = productService.getProductsByRestaurantId(restaurant.getId());
                    if (products.isEmpty()) {
                        this.ln("Aucun produit trouvé pour ce restaurant.");
                    } else {
                        for (Product product : products) {
                            productCLI.displayProduct(product);
                        }
                    }
                } catch (ProductServiceException e) {
                    throw new RuntimeException(e);
                }
            }
        }
    }
}
