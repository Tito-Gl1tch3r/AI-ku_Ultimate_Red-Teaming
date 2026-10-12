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
@WebServlet(name = "AdminAddItem", urlPatterns = {"/AdminAddItem"})
public class AdminAddItem extends HttpServlet {

    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        try {
            int quant=Integer.parseInt(request.getParameter("quant"));
            int itid=Integer.parseInt(request.getParameter("itid"));
            Item it=Itemdao.viewItem(itid);
            it.setQuantity(it.getQuantity()+quant);
            Itemdao.updateItem(it);
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(AdminAddItem.class.getName()).log(Level.SEVERE, null, ex);
        }
        response.sendRedirect("manageitems.jsp");
    }

}
