package de.mide.room.abkverz.helpers;

import android.app.AlertDialog;
import android.content.Context;


/**
 * Klasse enthält Hilfsmethoden für Erzeugen von Dialogen.
 * <br><br>
 *
 * This file is licensed under the terms of the BSD 3-Clause License.
 */
public class DialogHelfer {

    /**
     * Hilfsmethode zur Anzeige eines Dialogs für Fehlermeldungen u.ä.
     *
     * @param context  Context (Selbstreferenz auf aufrufende Activity).
     *
     * @param title  Dialog-Titel, z.B. "Fehler".
     *
     * @param nachricht  Eigentlicher Text des Dialogs.
     */
    public static void zeigeDialog(Context context, String title, String nachricht) {

        AlertDialog.Builder dialogBuilder = new AlertDialog.Builder(context);
        dialogBuilder.setTitle(title);
        dialogBuilder.setMessage(nachricht);

        dialogBuilder.setPositiveButton( "Weiter", null );
        dialogBuilder.setCancelable(false);

        AlertDialog dialog = dialogBuilder.create();
        dialog.show();
    }

}
