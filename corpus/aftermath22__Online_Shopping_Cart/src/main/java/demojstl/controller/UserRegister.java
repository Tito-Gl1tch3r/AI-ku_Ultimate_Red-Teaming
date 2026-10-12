/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/JSP_Servlet/Servlet.java to edit this template
 */
package demojstl.controller;

import demojstl.bean.User;
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

/**
 *
 * @author Keval
 */
@WebServlet(name = "UserRegister", urlPatterns = {"/UserRegister"})
public class UserRegister extends HttpServlet {
    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String uname=request.getParameter("uname");
        int uid=Integer.parseInt(request.getParameter("uid"));
        String pass=request.getParameter("pass");
        System.out.println("uname : "+uname+" pass: "+pass);
        User u=new User(uid,uname,pass);
        try {
            if(Userdao.viewUser(uid)==null){
                Userdao.insertUser(u);
                response.sendRedirect("index.jsp");
            }
            else{
                PrintWriter out=response.getWriter();
                out.println("Enter a different ID , this one is already registered ! ");
                response.sendRedirect("usereg.jsp");
            }
        } catch (SQLException | ClassNotFoundException  ex) {
            Logger.getLogger(UserRegister.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    
}
