package de.mide.room.abkverz.db;

import androidx.room.Dao;
import androidx.room.Insert;
import androidx.room.Query;
import androidx.room.Transaction;

import java.util.List;


/**
 * Data Access Object für Ausführung der CRUD-Operation auf den DB-Tabellen.
 * <br><br>
 *
 * DAO ist eine abstrakte Klasse und kein Interface, weil eine Methode mit Implementierung
 * enthalten ist, nämlich {@code insert(AbkEntity, BedeutungEntity)}.
 *
 * This project is licensed under the terms of the BSD 3-Clause License.
 */
@Dao
public abstract class AbkVerzDao {

    /**
     * DAO-Methode muss als {@code Transaction} annotiert werden, weil zwei Queries
     * ausgeführt werden.
     *
     * @param suchbegriff  Suchbegriff, es sollte vor Aufruf die Methode {@code trim()}
     *                     aufgerufen worden sein.
     *
     * @return  Bedeutungen für Abkürzung in {@code suchbegriff}; ist {@code null} wenn
     *          nichts gefunden.
     */
    @Transaction
    @Query("SELECT * FROM AbkEntity WHERE abkuerzung = :suchbegriff")
    public abstract AbkMitBedeutungen getBedeutungenFuerAbk(String suchbegriff);


    /**
     * Neue Abkürzung in DB-Tabelle einfügen; sollte nur DAO-intern verwendet werden.
     *
     * @param abk  Abkürzungs-Objekt.
     *
     * @return  ID der neu eingefügten Abkürzung.
     */
    @Insert
    public abstract long insert(AbkEntity abk);


    /**
     * Neue Bedeutung in DB-Tabelle einfügen; sollte nur DAO-intern verwendet werden.
     *
     * @param bedeutung  Bedeutungs-Objekt.
     *
     * @return  ID der neu eingefügten Bedeutung
     */
    @Insert
    public abstract long insert(BedeutungEntity bedeutung);


    /**
     * Methode fügt Abkürzung und erste Bedeutung hinzu, oder fügt weitere
     * Bedeutung zu bereits vorhandener Abkürzung hinzu.
     *
     * Siehe auch <a href="https://stackoverflow.com/a/53361969">hier</a>.
     * <br><br>
     *
     * Methode muss als {@code Transaction} deklariert sein, damit die beiden in der Methode
     * durchgeführten DB-Operationen atomar sind.
     *
     * @param abk Abkürzung, zu der eine Bedeutung hinzuzufügen ist.
     *
     * @param bedeutung  Neue Bedeutung für {@code abk}; Wert für {@code abkRefId}
     *                   wird in der Methode gesetzt.
     *
     * @return  {@code true} wenn es sich um die erste Bedeutung für {@code abk}
     *          handelte, ansonsten {@code false}.
     */
    @Transaction
    public boolean insert(AbkEntity abk, BedeutungEntity bedeutung) {

        boolean ersteBedeutung = false;

        String abkNormiert = abk.abkuerzung.trim().toUpperCase();
        AbkMitBedeutungen abkMitBedeutungen = getBedeutungenFuerAbk(abkNormiert);

        long abkId = -1;
        if (abkMitBedeutungen == null) { // neue Abkürzung einfügen

            abkId = insert(abk);
            ersteBedeutung = true;

        } else { // Weitere Bedeutung für bereits vorhandene Abkürzung einfügen

            abkId = abkMitBedeutungen.abk.abkid;
            ersteBedeutung = false;
        }

        bedeutung.abkRefId = abkId;
        insert(bedeutung);

        return ersteBedeutung;
    }

}
