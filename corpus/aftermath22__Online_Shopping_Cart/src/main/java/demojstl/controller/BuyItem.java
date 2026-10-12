/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/JSP_Servlet/Servlet.java to edit this template
 */
package demojstl.controller;

import demojstl.bean.Cart;
import demojstl.bean.Item;
import demojstl.bean.User;
import demojstl.dao.Cartdao;
import demojstl.dao.Itemdao;
import demojstl.dao.Userdao;
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
@WebServlet(name = "BuyItem", urlPatterns = {"/BuyItem"})
public class BuyItem extends HttpServlet {

    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws IOException
             {
                try {
                    HttpSession session=request.getSession();
                    int quant=Integer.parseInt(request.getParameter("quant"));
//                    System.out.println("i bought : "+quant);
                    
                    int id=Integer.parseInt(request.getParameter("itid"));
//                    System.out.println("i bought itid : "+id);
                    int uid=(int)session.getAttribute("uid");
//                    System.out.println("i am : "+uid);
                    Cart u ;
                    Item it ; 
                    
                    it = Itemdao.viewItem(id);
                    it.setQuantity((it.getQuantity()-quant));
                    
                    u = Cartdao.viewCart(uid,id);
                    
                    if(u==null){
                        u=new Cart(uid,uid,it.getItname(),(it.getPrice()*quant),id,quant);
                        Cartdao.insertCart(u);
                    }else{
                        u.setQuantity((u.getQuantity()+quant));
                        u.setPrice((u.getQuantity()*it.getPrice()));
                        Cartdao.updateCart(u,id);
                    }
                    if(it.getQuantity()==0){
                        Itemdao.deleteItem(id);
                    }
                    else{
                        Itemdao.updateItem(it);
                    }
                    
                } catch (ClassNotFoundException | SQLException ex) {
                    Logger.getLogger(BuyItem.class.getName()).log(Level.SEVERE, null, ex);
                }
                
                response.sendRedirect("shopitems.jsp");
            }
            

            
    }


