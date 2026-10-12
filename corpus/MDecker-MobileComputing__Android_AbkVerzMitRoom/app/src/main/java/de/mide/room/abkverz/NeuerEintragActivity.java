package de.mide.room.abkverz;

import android.os.Bundle;
import android.view.View;
import android.view.WindowManager;
import android.widget.EditText;
import static de.mide.room.abkverz.helpers.DialogHelfer.zeigeDialog;
import androidx.appcompat.app.AppCompatActivity;

import de.mide.room.abkverz.db.AbkEntity;
import de.mide.room.abkverz.db.AbkVerzDao;
import de.mide.room.abkverz.db.BedeutungEntity;
import de.mide.room.abkverz.db.MeineDatenbank;


/**
 * Activity zum Anlegen von neuen Abkürzungen oder dem Hinzufügen von
 * neuen Bedeutungen zu bestehenden Abkürzungen.
 * <br><br>
 *
 * This project is licensed under the terms of the BSD 3-Clause License.
 */
public class NeuerEintragActivity extends AppCompatActivity {

    /** UI-Element zur Eingabe der neuen Abkürzung. */
    private EditText _abkEditText = null;

    /** UI-Element zur Eingabe der neuen Bedeutung. */
    private EditText _bedeutungEditText = null;

    /** Data Access Object für CRUD-Operationen. */
    private AbkVerzDao _dao = null;


    /**
     * Lifecycle-Methode zur Initialisierung des Activity-Objekts.
     */
    @Override
    protected void onCreate(Bundle savedInstanceState) {

        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_neuer_eintrag);

        setTitle("Abk/Bedeutungen erfassen");

        _abkEditText       = findViewById(R.id.editTextNeueAbk      );
        _bedeutungEditText = findViewById(R.id.editTextNeueBedeutung);

        MeineDatenbank mdb = MeineDatenbank.getSingletonInstance(this);
        _dao = mdb.abkverzDao();

        // https://stackoverflow.com/a/49177973
        getWindow().setFlags( WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
                              WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS );
    }


    /**
     * Event-Handler für "Einfügen"-Button.
     *
     * @param view  Button, der Event ausgelöst hat.
     */
    public void onButtonEinfuegen(View view) {

        String abkuerzungTrimmed = _abkEditText.getText().toString().trim();
        String bedeutungTrimmed  = _bedeutungEditText.getText().toString().trim();

        if (abkuerzungTrimmed.length() == 0) {

            zeigeDialog( this, "Ungültige Eingabe",
                    "Keine Abkürzung eingegeben.");
            return;
        }
        if (bedeutungTrimmed.length() == 0) {

            zeigeDialog( this, "Ungültige Eingabe",
                    "Keine Bedeutung eingegeben.");
            return;
        }

        // Entites erstellen
        AbkEntity abkEntity = new AbkEntity();
        abkEntity.abkuerzung = abkuerzungTrimmed.toUpperCase(); // Abkürzung wird auf Großbuchstaben normiert!

        BedeutungEntity bedeutungEntity = new BedeutungEntity();
        bedeutungEntity.bedeutung = bedeutungTrimmed;

        // Eigentliche Einfüge-Operation
        boolean ersteBedeutung = _dao.insert(abkEntity, bedeutungEntity);
        if (ersteBedeutung) {

            zeigeDialog(this, "Erfolg",
                    "Erste Bedeutung für Abkürzung \"" + abkuerzungTrimmed + "\" eingefügt.");
        } else {

            zeigeDialog(this, "Erfolg",
                    "Weitere Bedeutung für Abkürzung \"" + abkuerzungTrimmed + "\" eingefügt.");
        }

        // Nur Eingabefeld für Bedeutung löschen, weil der Nutzer für Abkürzung vielleicht noch
        // eine weitere Bedeutung eingeben möchte.
        _bedeutungEditText.setText("");
    }


    /**
     * Event-Handler für Button zur Rückkehr zur {@code MainActivity}.
     *
     * @param view  Button, der Event ausgelöst hat.
     */
    public void onButtonZurueck(View view) {

        finish();
    }

}
