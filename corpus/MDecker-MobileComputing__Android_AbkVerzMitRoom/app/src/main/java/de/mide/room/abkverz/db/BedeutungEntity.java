package de.mide.room.abkverz.db;


import androidx.annotation.NonNull;
import androidx.room.Entity;
import androidx.room.PrimaryKey;


/**
 * Entity für Tabelle mit Bedeutungen.<br><br>
 *
 * Eine Bedeutung referenziert über eine Fremdschlüsselbeziehung
 * eine Abkürzung, wobei dieselbe Abkürzung von verschiedenen Bedeutungen referenziert werden
 * kann.
 * <br><br>
 *
 * This project is licensed under the terms of the BSD 3-Clause License.
 */
@Entity
public class BedeutungEntity {

    @PrimaryKey(autoGenerate = true)
    @NonNull
    public int bedeutungid;

    /** Attribut für Fremdschlüsselbeziehung. */
    public long abkRefId;

    /** Eine Bedeutung für eine bestimmte Abkürzung, z.B. "Karlsruher Sportclub" für "KSC". */
    @NonNull
    public String bedeutung;
}
