package ch.hearc.ig.orderresto.presentation.cli;

import ch.hearc.ig.orderresto.application.Main;
import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.business.Customer;
import ch.hearc.ig.orderresto.business.OrganizationCustomer;
import ch.hearc.ig.orderresto.business.PrivateCustomer;
import ch.hearc.ig.orderresto.persistence.exceptions.CustomerPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.ProductPersistenceException;
import ch.hearc.ig.orderresto.persistence.exceptions.RestaurantPersistenceException;
import ch.hearc.ig.orderresto.persistence.mappers.CustomerMapper;
import ch.hearc.ig.orderresto.presentation.AbstractCLI;
import ch.hearc.ig.orderresto.service.CustomerService;
import ch.hearc.ig.orderresto.service.exceptions.CustomerServiceException;
import oracle.as.management.opmn.integrator.OpmnIntegrator;

import java.sql.SQLException;
import java.util.Objects;

public class CustomerCLI extends AbstractCLI {

    private final CustomerService customerService = new CustomerService();

    protected Customer createCustomer(boolean isPrivateCustomer) {
        this.ln("Quelle est votre adresse email?");
        String email = this.readEmailFromUser();
        this.ln("Quel est votre numéro de téléphone?");
        String phone = this.readStringFromUser();
        Address address = (new AddressCLI()).getNewAddress();

        if (isPrivateCustomer) {
            this.ln("Quel est votre prénom ?");
            String firstName = this.readStringFromUser();
            this.ln("Quel est votre nom ?");
            String lastName = this.readStringFromUser();
            this.ln("Êtes-vous un homme ou une femme (H/F) ?");
            String gender = this.readChoicesFromUser(new String[]{"H", "F"});
            gender = Objects.equals(gender, "H") ? "O" : "N"; // Simplified gender assignment

            return new PrivateCustomer(null, phone, email, address, gender, firstName, lastName);
        } else {
            this.ln("Quel est le nom de votre organisation ?");
            String name = this.readStringFromUser();
            this.ln(String.format("%s est une société anonyme (SA) ?, une association (A) ou une fondation (F) ?", name));
            String legalForm = this.readChoicesFromUser(new String[]{"SA", "A", "F"});

            return new OrganizationCustomer(null, phone, email, address, name, legalForm);
        }
    }

    public Customer addCustomer() throws CustomerServiceException {
        this.ln("Type de client : 1. Client Privé, 2. Organisation");
        int choice = this.readIntFromUser(1, 2);
        Customer customer = createCustomer(choice == 1);

        customerService.addCustomer(customer);

        this.ln("Client ajouté avec succès !");
        return customer ;
    }

    public Customer getExistingCustomer() throws CustomerServiceException, RestaurantPersistenceException, SQLException, CustomerPersistenceException, ProductPersistenceException {
        Customer customer;
        while (true) {
            this.ln("Quelle est votre adresse email?");
            String email = this.readEmailFromUser();

            customer = customerService.getExistingCustomer(email);
            if (customer != null) {
                return customer;
            } else {
                this.ln("Aucun client trouvé avec cet email.");
                this.ln("Voulez-vous réessayer? [oui / non]");
                String response = this.readStringFromUser();
                if (!response.equalsIgnoreCase("oui")) {
                    new MainCLI().run();
                    return null;
                }
            }
        }
    }

}
