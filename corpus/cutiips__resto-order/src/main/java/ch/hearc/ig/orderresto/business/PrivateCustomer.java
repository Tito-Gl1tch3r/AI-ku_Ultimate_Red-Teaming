package ch.hearc.ig.orderresto.business;

public class PrivateCustomer extends Customer {

    private String gender;
    private String firstName;
    private String lastName;

    public PrivateCustomer(Long id, String phone, String email, Address address, String gender, String firstName, String lastName) {
        super(id, phone, email, address);
        this.gender = gender;
        this.firstName = firstName;
        this.lastName = lastName;
    }

    public String getGender() {
        return gender;
    }

    public String getFirstName() {
        return firstName;
    }

    public String getLastName() {
        return lastName;
    }
    public void setFirstName(String firstName) {
        this.firstName = firstName;
    }

    public void setPhoneNumber(String phone) {
        super.setPhoneNumber(phone);
    }

    public String getPhoneNumber() {
        return super.getPhoneNumber();
    }

    public void setLastName(String lastName) {
        this.lastName = lastName;
    }


}