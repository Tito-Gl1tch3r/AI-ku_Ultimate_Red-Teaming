package snapwork.com.mohittest;

import android.content.Intent;
import android.os.Bundle;
import android.support.design.widget.TabLayout;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentManager;
import android.support.v4.app.FragmentPagerAdapter;
import android.support.v4.view.ViewPager;
import android.support.v7.app.AppCompatActivity;
import android.support.v7.widget.Toolbar;
import android.util.Log;

import com.google.android.gms.maps.CameraUpdate;
import com.google.android.gms.maps.CameraUpdateFactory;
import com.google.android.gms.maps.GoogleMap;
import com.google.android.gms.maps.OnMapReadyCallback;
import com.google.android.gms.maps.SupportMapFragment;
import com.google.android.gms.maps.model.LatLng;
import com.google.android.gms.maps.model.LatLngBounds;
import com.google.android.gms.maps.model.Marker;
import com.google.android.gms.maps.model.MarkerOptions;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

public class MainActivity extends AppCompatActivity implements OnMapReadyCallback, GoogleMap.OnMarkerClickListener{

    private static final String TAG = MainActivity.class.getSimpleName();
    private List<Offer> offersList;
    private GoogleMap map;
    private ListFragment listFragment;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        Toolbar toolbar = (Toolbar) findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);

        getSupportActionBar().setDisplayHomeAsUpEnabled(false);

        ViewPager viewPager = (ViewPager) findViewById(R.id.viewpager);
        setupViewPager(viewPager);

        TabLayout tabLayout = (TabLayout) findViewById(R.id.tabs);
        tabLayout.setupWithViewPager(viewPager);

        loadOffers();
    }

    private void loadOffers() {
        ApiInterface apiService = ApiClient.getClient().create(ApiInterface.class);

        Call<List<Offer>> call = apiService.getAllOffers();
        call.enqueue(new Callback<List<Offer>>() {
            @Override
            public void onResponse(Call<List<Offer>>call, Response<List<Offer>> response) {
                offersList = response.body();
                Log.e(TAG, "Size of List=" + offersList.size());
                updateListItems();
                List<Marker> markers = plotOffers(map);
                if (!markers.isEmpty()) {
                    updateFocusToMarkers(markers);
                }
            }

            @Override
            public void onFailure(Call<List<Offer>>call, Throwable t) {
                // Log error here since request failed
                Log.e(TAG, t.toString());
            }
        });
    }

    private List<Marker> plotOffers(GoogleMap googleMap) {
        List<Marker> markers = new ArrayList<>();
        if (googleMap != null && offersList != null) {
            for (Offer offer : offersList) {
                Marker marker = googleMap.addMarker(new MarkerOptions()
                        .title(offer.getName())
                        .position(new LatLng(offer.getLAT(), offer.getLON()))
                );
                marker.setTag(offer);
                markers.add(marker);
            }
        }
        if (listFragment != null) {
            listFragment.loadReloadData();
        }
        return markers;
    }

    private void setupViewPager(ViewPager viewPager) {
        ViewPagerAdapter adapter = new ViewPagerAdapter(getSupportFragmentManager());
        listFragment = ListFragment.newInstance();
        adapter.addFragment(listFragment, getString(R.string.list_tab));
        SupportMapFragment supportMapFragment = SupportMapFragment.newInstance();
        supportMapFragment.getMapAsync(this);
        adapter.addFragment(supportMapFragment, getString(R.string.maps_tab));
        viewPager.setAdapter(adapter);
    }

    @Override
    public boolean onMarkerClick(Marker marker) {
        Log.d(TAG, "Marker = " + marker + " Title = " + marker.getTitle() + " Object = " + marker.getTag());
        openOfferDetails((Offer)marker.getTag());
        return false;
    }

    @Override
    public void onMapReady(GoogleMap googleMap) {
        map = googleMap;
        googleMap.setOnMarkerClickListener(this);
        List<Marker> markers = plotOffers(map);
        if (!markers.isEmpty()) {
            updateFocusToMarkers(markers);
        }
    }

    private void updateFocusToMarkers(List<Marker> markers) {
        LatLngBounds.Builder builder = new LatLngBounds.Builder();
        for (Marker marker : markers) {
            builder.include(marker.getPosition());
        }
        LatLngBounds bounds = builder.build();
        int padding = 50; // offset from edges of the map in pixels
        CameraUpdate cameraUpdate = CameraUpdateFactory.newLatLngBounds(bounds, padding);
        map.moveCamera(cameraUpdate);
    }

    private class ViewPagerAdapter extends FragmentPagerAdapter {
        private final List<Fragment> mFragmentList = new ArrayList<>();
        private final List<String> mFragmentTitleList = new ArrayList<>();

        ViewPagerAdapter(FragmentManager manager) {
            super(manager);
        }

        @Override
        public Fragment getItem(int position) {
            return mFragmentList.get(position);
        }

        @Override
        public int getCount() {
            return mFragmentList.size();
        }

        public void addFragment(Fragment fragment, String title) {
            mFragmentList.add(fragment);
            mFragmentTitleList.add(title);
        }

        @Override
        public CharSequence getPageTitle(int position) {
            return mFragmentTitleList.get(position);
        }
    }

    public List<Offer> getOffersList() {
        return offersList;
    }

    public void openOfferDetails(Offer offer) {
        Log.d(TAG, "Offer = " + offer);
        Intent intent = new Intent(this, OffersActivity.class);
        intent.putExtra(OffersActivity.OFFER_OBJECT, offer);
        startActivity(intent);
    }

    @Override
    protected void onResume() {
        super.onResume();
        updateListItems();
    }

    private void updateListItems() {
        Set<String> storedOffers = ((App)getApplication()).offerIDList;
        if (offersList != null) {
            for (Offer offer : offersList) {
                if (storedOffers.contains(offer.getOFFER_ID())) {
                    offer.setMarked(true);
                } else {
                    offer.setMarked(false);
                }
            }
            listFragment.loadReloadData();
        }
    }
}
