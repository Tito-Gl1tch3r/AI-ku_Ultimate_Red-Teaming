/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/JSP_Servlet/Servlet.java to edit this template
 */
package demojstl.controller;

import java.io.IOException;
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
@WebServlet(name = "AdminLogin", urlPatterns = {"/AdminLogin"})
public class AdminLogin extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        String us=request.getParameter("uid");
        int uid=Integer.parseInt(us);
        String pass=request.getParameter("pass");
        if(uid==-1 && pass.equals("1234")){
            HttpSession session=request.getSession();
            session.setAttribute("username", "Admin");
            response.sendRedirect("admintask.jsp");
        }else{
            response.sendRedirect("index.jsp");
        }
    }

    
}
