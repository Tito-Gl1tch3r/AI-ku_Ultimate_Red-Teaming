package snapwork.com.mohittest;

import java.io.Serializable;

/**
 * Created by snap34 on 11/8/17.
 */

public class Offer implements Serializable{
    private String OFFER_ID;
    private String address;
    private String name;
    private double LAT;
    private double LON;
    private boolean isMarked;

    public String getOFFER_ID() {
        return OFFER_ID;
    }

    public void setOFFER_ID(String OFFER_ID) {
        this.OFFER_ID = OFFER_ID;
    }

    public String getAddress() {
        return address;
    }

    public void setAddress(String address) {
        this.address = address;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public double getLAT() {
        return LAT;
    }

    public void setLAT(double LAT) {
        this.LAT = LAT;
    }

    public double getLON() {
        return LON;
    }

    public void setLON(double LON) {
        this.LON = LON;
    }

    public boolean isMarked() {
        return isMarked;
    }

    public void setMarked(boolean marked) {
        isMarked = marked;
    }
}
