/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package demojstl.bean;


/**
 *
 * @author Keval
 */
public class Cart {
    private int cid;
    private int uid;
    private int itid;
    private String itname;
    private int price;
    private int quantity;

    public Cart() {
    }

    public Cart(int cid, int uid, String itname, int price, int itid, int quantity) {
        this.cid = cid;
        this.uid = uid;
        this.itname = itname;
        this.price = price;
        this.itid = itid;
        this.quantity = quantity;
    }

    /**
     * @return the cid
     */
    public int getCid() {
        return cid;
    }

    /**
     * @param cid the cid to set
     */
    public void setCid(int cid) {
        this.cid = cid;
    }

    /**
     * @return the uid
     */
    public int getUid() {
        return uid;
    }

    /**
     * @param uid the uid to set
     */
    public void setUid(int uid) {
        this.uid = uid;
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
     * @return the price
     */
    public int getPrice() {
        return price;
    }

    /**
     * @param price the price to set
     */
    public void setPrice(int price) {
        this.price = price;
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
        return "Cart{" + "cid=" + cid + ", uid=" + uid + ", itname=" + itname + ", price=" + price + ", itid=" + itid + ", quantity=" + quantity + '}';
    }

    
    
}
