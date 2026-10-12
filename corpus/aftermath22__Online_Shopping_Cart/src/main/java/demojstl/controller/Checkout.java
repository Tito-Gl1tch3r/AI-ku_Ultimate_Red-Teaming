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
import java.util.ArrayList;
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
@WebServlet(name = "Checkout", urlPatterns = {"/Checkout"})
public class Checkout extends HttpServlet {

    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        try {
            HttpSession session=request.getSession();
            int uid=(int)session.getAttribute("uid");
            ArrayList<Cart> cs=Cartdao.getAllCartItems(uid);
            if(cs!=null){
                for(Cart x: cs){
//                        Item it=Itemdao.viewItem(x.getItid());
//                        int quant=x.getQuantity();
                        int itid=x.getItid();
                        
//                        
//                        if(it==null){
//                            
//                            it=new Item(x.getCid(),x.getItname(),x.getQuantity(),(x.getPrice()/x.getQuantity()));
//                            Itemdao.insertItem(it);
//                            
//                        }
//                        else{
//                            
//                            it.setQuantity(quant+it.getQuantity());
//                            Itemdao.updateItem(it);
//                        }
                        
                        Cartdao.deleteCart(uid, itid);
                }
            }
            response.sendRedirect("thankyou.jsp");
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(Checkout.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

}
