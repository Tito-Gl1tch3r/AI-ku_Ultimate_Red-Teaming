package ch.hearc.ig.orderresto.persistence.utils;

import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import ch.hearc.ig.orderresto.business.Address;
import oracle.jdbc.internal.XSCacheOutput;

public class AddressUtils {

    public static void setPreparedStatementAddress(PreparedStatement stmt, Address address, int startIndex) throws SQLException {
        stmt.setString(startIndex, address.getPostalCode());
        stmt.setString(startIndex + 1, address.getLocality());
        stmt.setString(startIndex + 2, address.getStreet());
        stmt.setString(startIndex + 3, address.getStreetNumber());
        stmt.setString(startIndex + 4, address.getCountryCode());
    }

    public static Address createAddressFromResultSet(ResultSet rs) throws SQLException {
        return new Address(
                rs.getString("pays"),
                rs.getString("code_postal"),
                rs.getString("localite"),
                rs.getString("rue"),
                rs.getString("num_rue")
        );

    }
}
