package de.mide.room.abkverz;

import android.content.Intent;
import android.os.Bundle;
import android.os.IBinder;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;

import java.util.List;

import de.mide.room.abkverz.db.AbkMitBedeutungen;
import de.mide.room.abkverz.db.AbkVerzDao;
import de.mide.room.abkverz.db.BedeutungEntity;
import de.mide.room.abkverz.db.MeineDatenbank;

import static de.mide.room.abkverz.helpers.DialogHelfer.zeigeDialog;


/**
 * Haupt-Activity der App; enthält die Funktion zur Abfrage von Abkürzungen.
 * <br><br>
 *
 * This project is licensed under the terms of the BSD 3-Clause License.
 */
public class MainActivity extends AppCompatActivity {

    /** Eingabefeld mit Abkürzung, nach der gesucht werden soll. */
    private EditText _textEditAbkZumSuchen = null;

    /** Button, mit dem die Suche nach einer Abkürzung gestartet wird. */
    private Button _buttonAbkSuche = null;

    /** Button, mit dem Activity zum Anlegen eines neuen Eintrags aufgerufen wird. */
    private Button _buttonNeuerEintrag = null;

    /** TextView-Element, mit dem die für eine Abkürzung gefundene Bedeutungen angezeigt werden. */
    private TextView _textViewBedeutungen = null;

    /** Data Access Object (DAO) für CRUD-Operationen (Singleton). */
    private AbkVerzDao _dao = null;


    /**
     * Lifecycle-Methode zur Initialisierung des Activity-Objekts.
     */
    @Override
    protected void onCreate(Bundle savedInstanceState) {

        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        setTitle("AbkVerz mit Room");

        _textEditAbkZumSuchen = findViewById(R.id.textEditFuerAbkZumSuchen       );
        _buttonAbkSuche       = findViewById(R.id.buttonStartAbkSuche            );
        _buttonNeuerEintrag   = findViewById(R.id.buttonNeueAbkEintragen         );
        _textViewBedeutungen  = findViewById(R.id.textViewFuerAnzeigeBedeutungen );

        MeineDatenbank meineDatenbank = MeineDatenbank.getSingletonInstance(this);
        _dao = meineDatenbank.abkverzDao();

        // https://stackoverflow.com/a/49177973
        getWindow().setFlags( WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                              WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS );
    }


    /**
     * Event-Handler für Button zum Auslösen einer Suche.
     *
     * @param view  Referenz auf Button, der das Event ausgelöst hat.
     */
    public void onSuchenButton(View view) {

        keyboardEinklappen();
        _textViewBedeutungen.setText("");

        String suchString = _textEditAbkZumSuchen.getText().toString().trim();
        if (suchString.length() == 0) {

            zeigeDialog(this, "Ungültige Eingabe",
                    "Bitte zulässige Abkürzung zum Suchen eingeben!");
            return;
        }

        suchString = suchString.toUpperCase();
        AbkMitBedeutungen abkMitBedeutungen = _dao.getBedeutungenFuerAbk(suchString);
        if ( abkMitBedeutungen == null ) {

            zeigeDialog(this, "Ergebnis",
                    "Keine Bedeutungen für \"" + suchString + "\" gefunden.");
            return;
        }

        String ergebnis = "";
        List<BedeutungEntity> bedeutungenListe = abkMitBedeutungen.bedeutungen;
        for (BedeutungEntity bedeutung: bedeutungenListe) {

            ergebnis += bedeutung.bedeutung + "\n";
        }
        _textViewBedeutungen.setText(ergebnis);
    }


    /**
     * Event-Handler zur Navigation auf Activity zur Erfassung neuer Abkürzungen und
     * Bedeutungen.
     *
     * @param view  Referenz auf Button, der das Event ausgelöst hat.
     */
    public void onNeuEintragButton(View view) {

        Intent intent = new Intent(this, NeuerEintragActivity.class);
        startActivity(intent);
    }


    /**
     * Virtuelles Keyboard wieder "einklappen". Lösung nach
     * <a href="https://stackoverflow.com/a/17789187/1364368">dieser Stackoverflow-Antwort</a>.
     */
    private void keyboardEinklappen() {

        InputMethodManager imm = (InputMethodManager) getSystemService(INPUT_METHOD_SERVICE);

        View view = getCurrentFocus();
        if (view == null) {

            view = new View(this);
        }

        IBinder token = view.getWindowToken();
        imm.hideSoftInputFromWindow(token, 0);
    }
}
