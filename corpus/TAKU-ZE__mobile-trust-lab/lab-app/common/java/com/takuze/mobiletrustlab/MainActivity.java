package com.takuze.mobiletrustlab;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity extends Activity implements View.OnClickListener {
    private LabStateStore stateStore;
    private TextView stateView;
    private Button claimButton;
    private Button resetButton;
    private Button diagnosticsButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        stateStore = new LabStateStore(this);
        setContentView(buildContent());
        refreshState();
    }

    private View buildContent() {
        int padding = (int) (24 * getResources().getDisplayMetrics().density);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(padding, padding, padding, padding);

        TextView title = new TextView(this);
        title.setText("Mobile Trust Lab");
        title.setTextSize(26);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        content.addView(title);

        TextView explanation = new TextView(this);
        explanation.setText("A purpose-built lab for comparing client-authoritative state with a tamper-evident local cache.");
        explanation.setTextSize(16);
        explanation.setPadding(0, padding / 2, 0, padding);
        content.addView(explanation);

        stateView = new TextView(this);
        stateView.setTextSize(18);
        stateView.setTypeface(Typeface.MONOSPACE);
        content.addView(stateView);

        claimButton = new Button(this);
        claimButton.setText("Claim demo reward");
        claimButton.setOnClickListener(this);
        content.addView(claimButton);

        resetButton = new Button(this);
        resetButton.setText("Reset lab state");
        resetButton.setOnClickListener(this);
        content.addView(resetButton);

        diagnosticsButton = new Button(this);
        diagnosticsButton.setText("Open admin diagnostics");
        diagnosticsButton.setOnClickListener(this);
        content.addView(diagnosticsButton);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        return scroll;
    }

    private void refreshState() {
        stateView.setText(stateStore.snapshot());
    }

    @Override
    public void onClick(View view) {
        if (view == claimButton) {
            boolean accepted = stateStore.claimReward();
            Toast.makeText(this, accepted ? "Reward accepted" : "Reward already claimed", Toast.LENGTH_SHORT).show();
            refreshState();
        } else if (view == resetButton) {
            stateStore.reset();
            refreshState();
        } else if (view == diagnosticsButton) {
            startActivity(new Intent(this, AdminActivity.class));
        }
    }
}
