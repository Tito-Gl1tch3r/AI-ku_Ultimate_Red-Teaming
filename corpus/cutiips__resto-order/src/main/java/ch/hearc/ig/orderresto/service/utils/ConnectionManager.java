package ch.hearc.ig.orderresto.service.utils;

import java.io.IOException;
import java.io.InputStream;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Properties;

public class ConnectionManager {
    protected static String url;
    protected static String username;
    protected static String password;

    static {
        loadProperties();
    }

    private static void loadProperties() {
        Properties prop = new Properties();
        try (InputStream input = ConnectionManager.class.getClassLoader().getResourceAsStream("config.properties")) {
            if (input == null) {
                System.out.println("Sorry, unable to find config.properties");
                return;
            }
            prop.load(input);
            url = prop.getProperty("db.url");
            username = prop.getProperty("db.username");
            password = prop.getProperty("db.password");

            if (url == null || username == null || password == null) {
                throw new RuntimeException("Database credentials are missing in config.properties");
            }
        } catch (IOException ex) {
            System.err.println("Error loading properties: " + ex.getMessage());
            throw new RuntimeException("Database configuration error", ex);
        }
    }

    public static Connection getConnection() throws SQLException {
        if (url == null || username == null || password == null) {
            throw new RuntimeException("Database credentials not loaded properly");
        }
        return DriverManager.getConnection(url, username, password);
    }
}
