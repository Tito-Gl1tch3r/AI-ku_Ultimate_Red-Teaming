package ch.hearc.ig.orderresto.presentation.cli;

import ch.hearc.ig.orderresto.business.Address;
import ch.hearc.ig.orderresto.presentation.AbstractCLI;
import ch.hearc.ig.orderresto.service.AddressService;

public class AddressCLI extends AbstractCLI {

    private final AddressService addressService;

    public AddressCLI() {
        this.addressService = new AddressService();
    }

    public Address getNewAddress() {
        this.ln("Quel est le code de votre pays? [CH]");
        String countryCode = this.readStringFromUser(2, 2, "CH");
        this.ln("Quel est le code postal de votre localité?");
        int postalCode = this.readIntFromUser(1000, 9999);
        this.ln("Quel est le nom de votre localité?");
        String locality = this.readStringFromUser();
        this.ln("Quel est le nom de votre rue?");
        String street = this.readStringFromUser();
        this.ln("Quel est le numéro de votre rue ? (optionnel)");
        String streetNumber = this.readStringFromUserAllowEmpty();

        return addressService.createAddress(
                countryCode,
                String.valueOf(postalCode),
                locality,
                street,
                streetNumber
        );
    }
}
