/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package demojstl.bean;


/**
 *
 * @author Keval
 */
public class User {
    private int uid;
    private String uname;
    private String pass;

    public User() {
    }

    public User(int uid, String uname, String pass) {
        this.uid = uid;
        this.uname = uname;
        this.pass = pass;
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
     * @return the uname
     */
    public String getUname() {
        return uname;
    }

    /**
     * @param uname the uname to set
     */
    public void setUname(String uname) {
        this.uname = uname;
    }

    /**
     * @return the pass
     */
    public String getPass() {
        return pass;
    }

    /**
     * @param pass the pass to set
     */
    public void setPass(String pass) {
        this.pass = pass;
    }

    @Override
    public String toString() {
        return "User{" + "uid=" + uid + ", uname=" + uname + ", pass=" + pass + '}';
    }
    
}
