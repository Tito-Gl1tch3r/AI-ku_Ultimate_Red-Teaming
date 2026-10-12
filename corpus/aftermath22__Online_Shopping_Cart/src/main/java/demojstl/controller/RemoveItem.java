/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/JSP_Servlet/Servlet.java to edit this template
 */
package demojstl.controller;

import demojstl.bean.Cart;
import demojstl.bean.Item;
import demojstl.dao.Cartdao;
import demojstl.dao.Itemdao;
import java.io.IOException;
import java.io.PrintWriter;
import java.sql.SQLException;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.servlet.ServletException;
import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

/**
 *
 * @author Keval
 */
@WebServlet(name = "RemoveItem", urlPatterns = {"/RemoveItem"})
public class RemoveItem extends HttpServlet {

    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        
        
        int quant=Integer.parseInt(request.getParameter("quant"));
        int itid=Integer.parseInt(request.getParameter("itid"));
        
        
        HttpSession session=request.getSession();
        int uid=(int)session.getAttribute("uid");
        
        
        Cart c = null;
        try {
            c = Cartdao.viewCart(uid, itid);
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
        }
        
        
        int price=(c.getPrice()/c.getQuantity());
            
            
            c.setQuantity((c.getQuantity()-quant));
            c.setPrice((c.getQuantity()*price));
            
        try {
            Cartdao.updateCart(c, itid);
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
        }
        
        
        Item it = null;
        try {
            
            it = Itemdao.viewItem(itid);
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
            
            
        }
        if(it==null){
            
            it=new Item(itid,c.getItname(),quant,price);
            
            
            try {
                Itemdao.insertItem(it);
            } catch (SQLException ex) {
                Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
            } catch (ClassNotFoundException ex) {
                Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
            }
            
            
        }else{
            
            
            it.setQuantity(it.getQuantity()+quant);
            
            
            try {
                Itemdao.updateItem(it);
            } catch (ClassNotFoundException | SQLException ex) {
                Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
            }
            
            
        }
        
        if(c.getQuantity()==0){
            
            try {
                Cartdao.deleteCart(uid,itid);
            } catch (ClassNotFoundException | SQLException ex) {
                Logger.getLogger(RemoveItem.class.getName()).log(Level.SEVERE, null, ex);
            }
            
        }
        response.sendRedirect("usercart.jsp");
    }

}
