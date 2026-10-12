/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package demojstl.bean;

/**
 *
 * @author Keval
 */
public class Item {
    private int itid;
    private String itname;
    private int quantity;
    private int price;
    public Item() {
    }

    public Item(int itid, String itname, int quantity,int price) {
        this.itid = itid;
        this.itname = itname;
        this.quantity = quantity;
        this.price=price;
        
    }

    /**
     * @return the itid
     */
    public int getItid() {
        return itid;
    }

    /**
     * @param itid the itid to set
     */
    public void setItid(int itid) {
        this.itid = itid;
    }

    /**
     * @return the itname
     */
    public String getItname() {
        return itname;
    }

    /**
     * @param itname the itname to set
     */
    public void setItname(String itname) {
        this.itname = itname;
    }

    /**
     * @return the quantity
     */
    public int getQuantity() {
        return quantity;
    }

    /**
     * @param quantity the quantity to set
     */
    public void setQuantity(int quantity) {
        this.quantity = quantity;
    }

    @Override
    public String toString() {
        return "Item{" + "itid=" + itid + ", itname=" + itname + ", quantity=" + quantity + ", price=" + price + '}';
    }


    public int getPrice() {
        return price;
    }

    public void setPrice(int price) {
        this.price = price;
    }
    
    
}
