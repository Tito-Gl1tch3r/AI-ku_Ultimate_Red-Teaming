/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/JSP_Servlet/Servlet.java to edit this template
 */
package demojstl.controller;

import demojstl.bean.Cart;
import demojstl.bean.Item;
import demojstl.dao.Cartdao;
import demojstl.dao.Itemdao;
import demojstl.dao.Userdao;
import java.io.IOException;
import java.io.PrintWriter;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

/**
 *
 * @author Keval
 */
@WebServlet(name = "RemoveUser", urlPatterns = {"/RemoveUser"})
public class RemoveUser extends HttpServlet {


    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        try {
            
            
            int duid=Integer.parseInt(request.getParameter("uid"));
            ArrayList<Cart> uc=Cartdao.getUserCart(duid);
            
            if(uc!=null && !uc.isEmpty()){
                for(Cart x: uc){
                    
                        Item itc=Itemdao.viewItem(x.getItid());
                        Item it=new Item(x.getItid(),x.getItname(),x.getQuantity(),(x.getPrice()/x.getQuantity()));
                        if(itc==null){
                            Itemdao.insertItem(it);
                        }else{
                            it.setQuantity(it.getQuantity()+itc.getQuantity());
                            Itemdao.updateItem(it);
                        } 
                }
                
            }
            Cartdao.deleteUserCart(duid);
            Userdao.deleteUser(duid);
            
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(RemoveUser.class.getName()).log(Level.SEVERE, null, ex);
        }
        response.sendRedirect("manageuser.jsp");
    }

    
}
