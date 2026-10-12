/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package demojstl.dao;
import demojstl.bean.*;
import demojstl.bean.Item;
import static demojstl.dao.Itemdao.getConnection;
import static demojstl.dao.Itemdao.viewItem;
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
public class Cartdao {
    public static Connection getConnection() throws ClassNotFoundException, SQLException
	{
		Connection con;
		Class.forName("com.mysql.jdbc.Driver");
	                con = DriverManager.getConnection("jdbc:mysql://localhost:3306/online_shopping", "root", "QWERTY");
		return con;
	}
    public static void insertCart(Cart c) throws SQLException, ClassNotFoundException{
            Connection con=getConnection();
            String sql="insert into cart(cid,uid,itid,itname,price,quantity) values(?,?,?,?,?,?);";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, c.getCid());
            st.setInt(2, c.getUid());
            st.setInt(3, c.getItid());
            st.setString(4, c.getItname());
            st.setInt(5, c.getPrice());
            st.setInt(6, c.getQuantity());
            st.executeUpdate();
        }
    
    public static Cart viewCart(int uid,int id) throws ClassNotFoundException, SQLException{
            Connection con=getConnection();
            if(id==-1){
                String sql="select * from cart where uid=?";
                PreparedStatement st=con.prepareStatement(sql);
                st.setInt(1,uid);
                ResultSet rs=st.executeQuery();
                while(rs.next()){
                    int cid=rs.getInt("cid");
                    int itid=rs.getInt("itid");
                    String itname=rs.getString("itname");
                    int price=rs.getInt("price");
                    int quantity=rs.getInt("quantity");
                    Cart c=new Cart(cid,uid,itname,price,itid,quantity);
                    return c;
                }
                return null;
            }
            String sql="select * from cart where uid=? and itid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1,uid);
            st.setInt(2,id);
            ResultSet rs=st.executeQuery();
            while(rs.next()){
                int cid=rs.getInt("cid");
                int itid=rs.getInt("itid");
                String itname=rs.getString("itname");
                int price=rs.getInt("price");
                int quantity=rs.getInt("quantity");
                Cart c=new Cart(cid,uid,itname,price,itid,quantity);
                return c;
            }
            return null;
        }
    
    public static ArrayList<Cart> getUserCart(int uid) throws ClassNotFoundException, SQLException{
        if(viewCart(uid,-1)==null){
            System.out.println("no such cart found ! ");
            return null;
        }
        ArrayList<Cart> uc=new ArrayList<>();
        Connection con=getConnection();
        String sql="select * from cart where uid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1,uid);
            ResultSet rs=st.executeQuery();
            while(rs.next()){
                int cid=rs.getInt("cid");
                int itid=rs.getInt("itid");
                String itname=rs.getString("itname");
                int price=rs.getInt("price");
                int quantity=rs.getInt("quantity");
                uc.add(new Cart(cid,uid,itname,price,itid,quantity));
            }
            if(uc.isEmpty())return null;
            return uc;
    }
    
    
    
    public static void deleteCart(int uid,int itid) throws ClassNotFoundException, SQLException{
            if(viewCart(uid,-1)==null){
                System.out.println("no such cart found ! ");
                return;
            }
            Connection con=getConnection();
            String sql="delete from cart where uid=? and itid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, uid);
            st.setInt(2, itid);
            st.executeUpdate();
        }
    
    public static void deleteUserCart(int uid) throws ClassNotFoundException, SQLException{
            if(viewCart(uid,-1)==null){
                System.out.println("no such cart found ! ");
                return;
            }
            Connection con=getConnection();
            String sql="delete from cart where uid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, uid);
            st.executeUpdate();
        }
    
    public static void updateCart(Cart c,int itid) throws ClassNotFoundException, SQLException{
            if(viewCart(c.getUid(),-1)==null){
                System.out.println("no such cart found to update ! ");
                return;
            }
            Connection con=getConnection();
            String sql="update cart set price=? , quantity=? where uid=? and itid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, c.getPrice());
            st.setInt(2,c.getQuantity());
            st.setInt(3, c.getUid());
            st.setInt(4, itid);
            st.executeUpdate();
        }
    
    public static ArrayList<Cart> getAllCartItems(int uid) throws ClassNotFoundException, SQLException{
            String sql="select * from cart order by uid";
            Connection con=getConnection();
            PreparedStatement st=con.prepareStatement(sql);
            ResultSet rs=st.executeQuery();
            ArrayList<Cart> ls=new ArrayList<>();
            while(rs.next()){
                Cart c=new Cart(rs.getInt("cid"),rs.getInt("uid"),rs.getString("itname"),rs.getInt("price"),rs.getInt("itid"),rs.getInt("quantity"));
                if(c.getUid()==uid)
                    ls.add(c);
            }
            if(ls.isEmpty()) return null;
            return ls;
        }
}
