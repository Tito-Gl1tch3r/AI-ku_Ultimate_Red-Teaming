package de.mide.room.abkverz.db;

import androidx.annotation.NonNull;
import androidx.room.Entity;
import androidx.room.PrimaryKey;


/**
 * Entity für Tabelle mit den Abkürzungen (aber nicht den Bedeutungen!); eine
 * Abkürzung kann eine oder mehrere Bedeutungen referenzieren. Eine Abkürzung
 * wird über eine Fremschlüsselbeziehung von einer oder mehreren Instanzen
 * von {@link BedeutungEntity} referenziert.
 * <br><br>
 *
 * This project is licensed under the terms of the BSD 3-Clause License.
 */
@Entity
public class AbkEntity {

    /** Eindeutiger Primärschlüssel für Abkürzung. */
    @PrimaryKey(autoGenerate = true)
    @NonNull
    public int abkid;

    /** Text der Abkürzung, z.B. "KSC"; muss immer auf Großbuchstaben normiert sein. */
    @NonNull
    public String abkuerzung;

}
