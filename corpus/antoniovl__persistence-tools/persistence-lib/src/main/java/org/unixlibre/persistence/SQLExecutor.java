package org.unixlibre.persistence;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.sql.Connection;
import java.sql.SQLException;
import java.sql.Statement;

/**
 *
 */
public class SQLExecutor {

    private static final Logger logger = LoggerFactory.getLogger(SQLExecutor.class);
    private final static String SQL_COMMENT = "--";
    private final static String END_OF_STATEMENT = ";";

    private Connection conn;

    public SQLExecutor(Connection conn) {
        this.conn = conn;
    }

    public void execute(String sql) throws SQLException, IOException {
        StringReader stringReader = new StringReader(sql);
        execute(stringReader);
    }

    public void execute(File file) throws SQLException, IOException {
        FileReader fileReader = new FileReader(file);
        execute(fileReader);
    }

    public void execute(InputStream inputStream) throws SQLException, IOException {
        InputStreamReader streamReader = new InputStreamReader(inputStream);
        execute(streamReader);
    }

    public void execute(Reader reader) throws SQLException, IOException {
        Statement stmt = null;
        StringBuilder sb = new StringBuilder(1024);
        String line;

        try (BufferedReader bufferedReader = new BufferedReader(reader)) {
            stmt = conn.createStatement();

            while ((line = bufferedReader.readLine()) != null) {
                if (isSQL(line)) {
                    sb.append(line);
                    if (line.endsWith(END_OF_STATEMENT)) {
                        sb.deleteCharAt(sb.length() - 1);
                        String sql = sb.toString();
                        logger.debug("statement: {}", sql);
                        stmt.execute(sql);
                        sb.setLength(0);
                    }
                }
            }
        } catch (SQLException | IOException ex) {
            logger.debug("SQL = {}", sb.toString());
            throw ex;
        } finally {
            if (stmt != null) {
                try {
                    stmt.close();
                } catch (SQLException se) {
                    logger.error("SQLException", se);
                }
            }
        }
    }

    private boolean isSQL(String s) {
        if (s == null) {
            return false;
        }
        String line = s.trim();
        return (line.length() > 0) &&
                (!line.startsWith(SQL_COMMENT));
    }
}
