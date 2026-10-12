/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/JSP_Servlet/Servlet.java to edit this template
 */
package demojstl.controller;

import demojstl.bean.Item;
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

/**
 *
 * @author Keval
 */
@WebServlet(name = "AdminAddItems", urlPatterns = {"/AdminAddItems"})
public class AdminAddItems extends HttpServlet {

    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        
        try {
            int itid=Integer.parseInt(request.getParameter("itid"));
            int itprice=Integer.parseInt(request.getParameter("itprice"));
            int quantity=Integer.parseInt(request.getParameter("quantity"));
            String itname=request.getParameter("itname");
            
            if(Itemdao.viewItem(itid)==null){
                
                Itemdao.insertItem(new Item(itid,itname,quantity,itprice));
                
            }
            response.sendRedirect("newitems.jsp");
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(AdminAddItems.class.getName()).log(Level.SEVERE, null, ex);
        }
        
    }    

}
