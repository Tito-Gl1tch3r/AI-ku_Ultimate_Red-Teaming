package snapwork.com.mohittest;

import android.graphics.Color;
import android.support.v7.widget.RecyclerView;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import java.util.List;

/**
 * Created by snap34 on 11/8/17.
 */

public class OffersAdapter extends RecyclerView.Adapter<OffersAdapter.OfferViewHolder> {

    private ListFragment fragment;
    private List<Offer> offerList;

    public class OfferViewHolder extends RecyclerView.ViewHolder {
        public TextView title, latitude, longitude;

        public OfferViewHolder(View view) {
            super(view);
            title = (TextView) view.findViewById(R.id.tvTitle);
            longitude = (TextView) view.findViewById(R.id.tvLong);
            latitude = (TextView) view.findViewById(R.id.tvLat);
        }
    }

    public OffersAdapter(ListFragment fragment, List<Offer> offerList) {
        this.fragment = fragment;
        this.offerList = offerList;
    }

    @Override
    public OfferViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
        View itemView = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.offer_item, parent, false);

        return new OfferViewHolder(itemView);
    }

    @Override
    public void onBindViewHolder(OfferViewHolder holder, int position) {
        final Offer offer = offerList.get(position);
        holder.title.setText(offer.getName());
        holder.longitude.setText("Longitude: " + offer.getLON());
        holder.latitude.setText("Latitude: " + offer.getLAT());
        holder.itemView.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View view) {
                fragment.showOfferDetailScreen(offer);
            }
        });
        if (offer.isMarked()) {
            holder.itemView.setBackgroundColor(Color.LTGRAY);
        } else {
            holder.itemView.setBackgroundColor(Color.TRANSPARENT);
        }
    }

    @Override
    public int getItemCount() {
        if (offerList != null) {
            return offerList.size();
        } else {
            return 0;
        }
    }
}