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
import java.sql.Statement;
import java.util.ArrayList;

/**
 *
 * @author Keval
 */
public class Userdao {
    public static Connection getConnection() throws ClassNotFoundException, SQLException
	{
		Connection con;
		Class.forName("com.mysql.jdbc.Driver");
                con = DriverManager.getConnection("jdbc:mysql://localhost:3306/online_shopping", "root", "QWERTY");
		return con;
	}
    
    public static void insertUser(User u) throws SQLException, ClassNotFoundException{
            Connection con=getConnection();
            String sql="insert into user(uid,uname,pass) values(?,?,?);";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, u.getUid());
            st.setString(2, u.getUname());
            st.setString(3, u.getPass());
            st.executeUpdate();
        }
    
    public static User viewUser(int uid) throws ClassNotFoundException, SQLException{
            Connection con=getConnection();
            String sql="select * from user where uid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, uid);
            ResultSet rs=st.executeQuery();
            while(rs.next()){
                int id=rs.getInt("uid");
                String name=rs.getString("uname");
                String pass=rs.getString("pass");
                User u=new User(id,name,pass);
                return u;
            }
            return null;
        }
    
    public static void deleteUser(int uid) throws ClassNotFoundException, SQLException{
            if(viewUser(uid)==null){
                System.out.println("no such item found ! ");
                return;
            }
            Connection con=getConnection();
            String sql="delete from user where uid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setInt(1, uid);
            st.executeUpdate();
        }
    
    public static void updateUser(User u) throws ClassNotFoundException, SQLException{
            if(viewItem(u.getUid())==null){
                System.out.println("no such item found to update ! ");
                return;
            }
            Connection con=getConnection();
            String sql="update item set uname=? pass=? where uid=?";
            PreparedStatement st=con.prepareStatement(sql);
            st.setString(1,u.getUname() );
            st.setString(2, u.getPass()); st.setInt(3, u.getUid());
            st.executeUpdate();
        }
    
    
    public static ArrayList<User> getAllUsers() throws ClassNotFoundException, SQLException{
            String sql="select uid,uname from user order by uid";
            Connection con=getConnection();
            PreparedStatement st=con.prepareStatement(sql);
            ResultSet rs=st.executeQuery();
            ArrayList<User> ls=new ArrayList<>();
            while(rs.next()){
//                System.out.println(rs.getString("itname"));
                User u=new User();
                u.setUid(rs.getInt("uid"));
                u.setUname(rs.getString("uname"));
                ls.add(u);
            }
            if(ls.isEmpty()) return null;
            return ls;
        }
    
}
