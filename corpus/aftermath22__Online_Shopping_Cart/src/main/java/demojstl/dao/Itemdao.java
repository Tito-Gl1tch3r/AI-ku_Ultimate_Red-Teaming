/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package demojstl.dao;
import demojstl.bean.*;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;

/**
 *
 * @author Keval
 */
public class Itemdao {
        public static Connection getConnection() throws ClassNotFoundException, SQLException
	{
		Connection con;
		Class.forName("com.mysql.jdbc.Driver");
                con = DriverManager.getConnection("jdbc:mysql://localhost:3306/online_shopping", "root", "QWERTY");
		return con;
	}
        public static void insertItem(Item i) throws SQLException, ClassNotFoundException{
            Connection con=getConnection();
            String sql="insert into item(itid,itname,quantity,price) values(?,?,?,?);";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1,i.getItid());
            st.setInt(3,i.getQuantity());
            st.setString(2, i.getItname());
            st.setInt(4, i.getPrice());
            st.executeUpdate();
        }
        
        public static Item viewItem(int itid) throws ClassNotFoundException, SQLException{
            Connection con=getConnection();
            String sql="select * from item where itid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1,itid);
            ResultSet rs=st.executeQuery();
            while(rs.next()){
                int id=rs.getInt("itid");
                String name=rs.getString("itname");
                int price=rs.getInt("price");
                int quant=rs.getInt("quantity");
                Item i=new Item(id,name,quant,price);
                return i;
            }
            return null;
        }
        
        public static void deleteItem(int itid) throws ClassNotFoundException, SQLException{
            if(viewItem(itid)==null){
                System.out.println("no such item found ! ");
                return;
            }
            Connection con=getConnection();
            String sql="delete from item where itid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, itid);
            st.executeUpdate();
        }
        public static void updateItem(Item i) throws ClassNotFoundException, SQLException{
            if(viewItem(i.getItid())==null){
                System.out.println("no such item found to update ! ");
                return;
            }
            Connection con=getConnection();
            String sql="update item set itname=? , price=? , quantity=? where itid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setString(1,i.getItname() );
            st.setInt(2, i.getPrice()); st.setInt(3, i.getQuantity()); st.setInt(4, i.getItid());
            st.executeUpdate();
        }
        
        public static ArrayList<Item> getAllItems() throws ClassNotFoundException, SQLException{
            String sql="select * from item order by itid";
            Connection con=getConnection();
            PreparedStatement st=con.prepareStatement(sql);
            ResultSet rs=st.executeQuery();
            ArrayList<Item> ls=new ArrayList<>();
            while(rs.next()){
//                System.out.println(rs.getString("itname"));
                Item it=new Item(rs.getInt("itid"),rs.getString("itname"),rs.getInt("quantity"),rs.getInt("price"));
                ls.add(it);
            }
            if(ls.isEmpty()) return null;
            return ls;
        }
}
