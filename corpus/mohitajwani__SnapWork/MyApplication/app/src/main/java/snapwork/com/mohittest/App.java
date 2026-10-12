package snapwork.com.mohittest;

import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;

import java.util.HashSet;
import java.util.Set;

/**
 * Created by Mohit Ajwani.
 */

public class App extends Application {

    private static final String SHARED_PREF = "MohitTest";
    private static final String OFFER_LIST = "OfferList";

    public Set<String> offerIDList = new HashSet<>();
    private SharedPreferences sharedPreferences;

    @Override
    public void onCreate() {
        super.onCreate();
        sharedPreferences = getSharedPreferences(SHARED_PREF, Context.MODE_PRIVATE);
        loadOfferList();
    }

    private void loadOfferList() {
        sharedPreferences = getSharedPreferences(SHARED_PREF, Context.MODE_PRIVATE);
        offerIDList = sharedPreferences.getStringSet(OFFER_LIST, new HashSet<String>());
    }

    public void updateOfferList(String offerId, boolean addOfferId) {
        if (addOfferId) {
            offerIDList.add(offerId);
        } else {
            offerIDList.remove(offerId);
        }
        SharedPreferences.Editor editor = sharedPreferences.edit();
        editor.putStringSet(OFFER_LIST, offerIDList);
        editor.apply();
    }
}
