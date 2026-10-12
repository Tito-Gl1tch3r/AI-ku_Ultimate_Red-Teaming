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
import javax.servlet.http.HttpSession;

/**
 *
 * @author Keval
 */
@WebServlet(name = "UserLogin", urlPatterns = {"/UserLogin"})
public class UserLogin extends HttpServlet {


    
    @Override
    protected void doGet(HttpServletRequest request, HttpServletResponse response)
            throws ServletException, IOException {
        int uid=Integer.parseInt(request.getParameter("uid"));
        String pass=request.getParameter("pass");
        User u=null;
        try {
            u = Userdao.viewUser(uid);
        } catch (ClassNotFoundException | SQLException ex) {
            Logger.getLogger(UserLogin.class.getName()).log(Level.SEVERE, null, ex);
        }
        if(u==null){
            response.sendRedirect("userlogin.jsp");
        }else{
            if(u.getPass().equals(pass)){
                HttpSession session=request.getSession();
                session.setAttribute("uid", u.getUid());
                session.setAttribute("username", u.getUname());
                response.sendRedirect("usertask.jsp");
            }else{
                response.sendRedirect("usertask.jsp");
            }
        }
    }

}
