package snapwork.com.mohittest;

import android.os.Bundle;
import android.support.v7.app.AppCompatActivity;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;

/**
 * Created by Mohit Ajwani.
 */

public class OffersActivity extends AppCompatActivity {

    private static final String TAG = OffersActivity.class.getSimpleName();

    public static final String OFFER_OBJECT = "Offer";

    private Button btnSaveDiscard;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_offers);

        final Offer offer = (Offer) getIntent().getExtras().getSerializable(OFFER_OBJECT);
        loadOfferData(offer);
        btnSaveDiscard = (Button) findViewById(R.id.btnSaveDiscard);
        updateButtonText(offer);
        btnSaveDiscard.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                if (offer.isMarked()) {
                    offer.setMarked(false);
                    ((App) getApplication()).updateOfferList(offer.getOFFER_ID(), false);
                } else {
                    offer.setMarked(true);
                    ((App) getApplication()).updateOfferList(offer.getOFFER_ID(), true);
                }
                updateButtonText(offer);
            }
        });
    }

    private void updateButtonText(Offer offer) {
        if (offer.isMarked()) {
            btnSaveDiscard.setText(getString(R.string.button_discard));
        } else {
            btnSaveDiscard.setText(getString(R.string.button_save));
        }
    }

    private void loadOfferData(Offer offer) {
        TextView tvOfferId = (TextView) findViewById(R.id.tvOfferIdValue);
        TextView tvTitleValue = (TextView) findViewById(R.id.tvTitleValue);
        TextView tvAddressValue = (TextView) findViewById(R.id.tvAddressValue);
        TextView tvLatValue = (TextView) findViewById(R.id.tvLatValue);
        TextView tvLonValue = (TextView) findViewById(R.id.tvLonValue);

        tvOfferId.setText(offer.getOFFER_ID());
        tvTitleValue.setText(offer.getName());
        tvAddressValue.setText(offer.getAddress());
        tvLatValue.setText("" + offer.getLAT());
        tvLonValue.setText("" + offer.getLON());
    }

}
