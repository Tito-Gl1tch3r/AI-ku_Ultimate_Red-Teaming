package de.mide.room.abkverz.db;

import android.content.Context;
import android.util.Log;

import androidx.room.Database;
import androidx.room.Room;
import androidx.room.RoomDatabase;


/**
 * Die Datenbank-Klasse enthält eine Getter-Methode für die DAOs.
 * In der Annotation für die Klasse selbst müssen unter dem Attribut {@code entities}
 * alle Entity-Klassen deklariert werden.
 * <br><br>
 *
 * This file is licensed under the terms of the BSD 3-Clause License.
 */
@Database(entities = {AbkEntity.class, BedeutungEntity.class}, version=1, exportSchema = false)
public abstract class MeineDatenbank extends RoomDatabase  {

    /**
     * Name der Datenbank-Datei, die von SQLite3 angelegt wird.
     * DB-Datei wird im Ordner {@code /data/data/de.mide.room.abkverz/databases}
     * gespeichert.
     */
    private static final String DB_DATEI_NAME = "abkverz.db";

    /** Referenz auf Singleton-Instanz, wird erst bei Bedarf erzeugt (lazy creation). */
    private static MeineDatenbank SINGLETON_INSTANCE = null;

    /**
     * Getter für DAO (Data Access Object). Die Geschäftslogik der App darf nur über DAOs
     * auf die Datenbank zugreifen.
     *
     * @return  Objekt für Ausführung CRUD-Operation auf Tabelle mit Lernkarten.
     */
    public abstract AbkVerzDao abkverzDao();


    /**
     * Getter für Singleton-Instanz der vorliegenden Klasse; bei Bedarf wird diese Instanz
     * erzeugt.
     *
     * @param context  Application Context, wird für evtl. Erzeugung der Singleton-Instanz
     *                 benötigt.
     *
     * @return  Singleton-Instanz von Datenbank-Objekt, von dem die DAOs geholt werden können.
     */
    public static MeineDatenbank getSingletonInstance(Context context) {

        if (SINGLETON_INSTANCE == null) {

            SINGLETON_INSTANCE =
                    Room.databaseBuilder(

                            context.getApplicationContext(),
                            MeineDatenbank.class,
                            DB_DATEI_NAME

                    ).allowMainThreadQueries().build();
        }

        return SINGLETON_INSTANCE;
    }

}
